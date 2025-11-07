import common
import db
import pandas as pd
import numpy as np
import psycopg2 as pg
from dotenv import dotenv_values
from psycopg2.extras import execute_batch, execute_values

config = dotenv_values(common.ENV_FILE)

KONDINSKY_PREFIX = "K"
ISHIM_PREFIX = "I"

kondinsky_rename_dict = {
    "№ случая": "referral_id",
    "Лок. Номер": "patient_id",
    "Дата рождения": "birthday",
    "Пол": "sex",
    "Предварительный диагноз": "diagnosis_code",
    "Наименование теста": "test_name",
    "Результат": "result",
    # Вероятней всего это не дата сдачи анализа,
    # а дата создания направления (чаще всего это может быть дата приема пациента).
    # Однако для простоты можем использовать эту колонку как дату сдачи анализа
    "Дата направления": "sampling_date",
    # "Национальность": "",
    # "№ анализа": "",
    # "Наименование анализа": "",
    # "№ теста": "",
    # "Отделение": "",
    # "Окончательный диагноз": "",
    # "№ карты": "",
    # "Тип": "",
}

ishim_rename_dict = {
    "Orders_ID": "referral_id",
    "PatientId": "patient_id",
    "Birthday": "birthday",
    "Sex": "sex",
    "DiagnosisCode": "diagnosis_code",
    "TestName": "test_name",
    "QuantResult": "result",
    "DateTimeSampling": "sampling_date",
    # "DateTime": "",
    # "RequestId": "",
    # "SampleId": "",
    # "LaboratoryId": "",
    # "OrganizationId": "",
    # "BiomaterialId": "",
    # "CountBiomaterial": "",
    # "NameUnit": "",
    # "Surname": "",
    # "Name_": "",
    # "Patronymic": "",
    # "HospitalDepartmentId": "",
    # "HospitalDepartmentName": "",
    # "DoctorId": "",
    # "DoctorFullName": "",
    # "TestId": "",
    # "Mnemonic": "",
    # "QualResult": "",
    # "UnitName": "",
    # "BoundRefer": "",
    # "Comment": "",
}


def load_kondinsky():
    files = (common.PRIVATE_DATA_DIR / "kondinsky").glob("**/*.parquet.gzip")
    dfs = []
    for file in files:
        df = pd.read_parquet(file)
        dfs.append(df)
    return pd.concat(dfs)


def load_ishim():
    return pd.read_parquet(common.PRIVATE_DATA_DIR / "ishim.parquet.gzip")


def load_reference():
    ref_file_path = common.DATA_DIR / "analysis-reference-new.xlsx"

    oak_ref = pd.read_excel(ref_file_path, sheet_name="Справочник ОАК")
    bak_ref = pd.read_excel(ref_file_path, sheet_name="Справочник БАК")

    oak_ref["ref_analysis_name"] = "Общий анализ крови"
    bak_ref["ref_analysis_name"] = "Биохимический анализ крови"

    ref = pd.concat([oak_ref, bak_ref])

    return ref


def ishim_date_converter(column):
    return pd.to_datetime(column, format="%d.%m.%Y", errors="coerce")


def kondinsky_date_converter(column):
    return pd.to_datetime(column, dayfirst=True, errors="coerce")


# Используется для предобработки данных в конкретном районе.
# Особенности предобработки задаются через параметры
def preprocess_district_data(
    df,
    rename_dict,
    reference,
    column_in_ref,
    id_prefix,
    date_converter,
    district_name,
):
    # Удаляем ненужные столбцы и переименовываем оставшиеся
    columns_to_save = rename_dict.keys()
    columns_to_drop = set(df.columns).difference(columns_to_save)
    df.drop(columns=columns_to_drop, inplace=True)
    df.rename(columns=rename_dict, inplace=True)

    # Сразу уберем много записей, чтобы не делать ненужные join'ы (ускорит процесс)
    df.dropna(subset=["result", "referral_id"], inplace=True)

    # Заменяем название тестов на справочные
    ref_cols = [
        column_in_ref,
        "ref_analysis_name",
        "ref_test_name",
        "ref_test_mnemonic",
    ]
    df = pd.merge(df, reference[ref_cols], left_on="test_name", right_on=column_in_ref)

    # Убираем колонки left_on и right_on
    df.drop(columns=["test_name", column_in_ref], inplace=True)

    # Создаем уникальные идентификаторы, чтобы случайно не было повторов
    df["referral_id"] = id_prefix + "_" + df["referral_id"].astype(str)
    df["patient_id"] = id_prefix + "_" + df["patient_id"].astype(str)

    # Не можем конвертировать дату в объединенном датасете,
    # потому что один из форматов всегда будет считаться ошибкой. Поэтому делаем здесь,
    # с использованием внешней функции
    df["sampling_date"] = date_converter(df["sampling_date"])
    df["birthday"] = date_converter(df["birthday"])

    # Поможет различать соединенные выборки
    df["district_name"] = district_name

    return df


def preprocess_united_data_inplace(df):
    # errors='coerce' запишет NA, если функция не смогла преобразовать значение

    # Стандартизируем пол
    sex_map = {1.0: "м", 2.0: "ж", "М": "м", "Ж": "ж"}
    df["sex"] = df["sex"].map(sex_map)

    # Стандартизируем разделитель
    result = df["result"].astype("string").str.replace(",", ".")
    df["result"] = pd.to_numeric(result, errors="coerce")

    # Посчитаем возраст код на момент сдачи
    df["age_when_sampling"] = df["sampling_date"].dt.year - df["birthday"].dt.year

    # Теперь удаляем строки, в которых что-то было где-то неправильно
    columns_to_ignore_dropna = ["ref_test_mnemonic"]
    columns_to_dropna = set(df.columns).difference(columns_to_ignore_dropna)
    df.dropna(subset=columns_to_dropna, inplace=True)


def get_list_of_tuples(df, columns=None):
    if columns is not None:
        df = df[columns]
    # Этот ребус это просто самый быстрый способ создать список кортежей
    return list(zip(*map(df.get, df)))


def import_districts(data, conn):
    data = data[["district_name"]]
    data = data.drop_duplicates()
    values = get_list_of_tuples(data)

    query = "INSERT INTO district (name) VALUES %s;"
    with conn:
        with conn.cursor() as cur:
            execute_values(cur, query, values)


def import_patients(data, conn):
    data = data[["patient_id", "sex", "birthday", "district_name"]]
    data = data.drop_duplicates("patient_id")
    values = get_list_of_tuples(data)

    query = """
INSERT INTO patient (
	import_id,
	gender,
	birthday,
	district_id
)
VALUES (
	%s, %s,	%s, (SELECT id FROM district WHERE name = %s)
);
"""

    with conn:
        with conn.cursor() as cur:
            execute_batch(cur, query, values)


def import_analysis(data, conn):
    data = data[["ref_analysis_name"]]
    data = data.drop_duplicates()
    values = get_list_of_tuples(data)

    query = "INSERT INTO analysis (name) VALUES %s;"
    with conn:
        with conn.cursor() as cur:
            execute_values(cur, query, values)


def import_tests(data, conn):
    data = data[["ref_test_name", "ref_test_mnemonic", "ref_analysis_name"]]
    data = data.drop_duplicates()
    values = get_list_of_tuples(data)

    query = """
INSERT INTO test (
	name,
	mnemonic,
	analysis_id
)
VALUES(
	%s, %s, (SELECT id FROM analysis WHERE name = %s)
)
"""

    with conn:
        with conn.cursor() as cur:
            execute_batch(cur, query, values)


def import_mkb(conn):
    mkb_file_path = common.DATA_DIR / "mkb.csv"
    mkb = pd.read_csv(mkb_file_path, sep=",")

    # Создаем колонку с идентификатором, он будет использоваться как первичный ключ в БД
    mkb.reset_index(names="id", inplace=True)
    mkb["id"] = mkb["id"] + 1  # В БД принято начинать с 1

    # Определяем родительский id. Этот Join выглядит как ошибка, но на самом деле
    # колонки не перепутаны
    mkb = pd.merge(
        left=mkb, left_on="parent_code", right=mkb, right_on="code", how="left"
    )

    # Удаляем лишние строки, переименовываем
    rename = {
        "id_x": "id",
        "code_x": "code",
        "name_x": "name",
        # "parent_code_x": "",
        "id_y": "parent_id",
        # "code_y": "",
        # "name_y": "",
        # "parent_code_y": "",
    }
    cols_to_drop = set(mkb.columns).difference(rename.keys())
    mkb.drop(columns=cols_to_drop, inplace=True)
    mkb.rename(columns=rename, inplace=True)

    mkb.drop_duplicates("id", inplace=True)
    mkb.replace(np.nan, None, inplace=True)  # NaN не может быть импортирован

    # Импортируем по уровням, чтобы не получить ситуацию, когда импортируется ребенок
    # с еще неимпортированным родителем - возникает ошибка ссылки таблицы саму на себя
    # (сортировкой по каким-либо колонкам проблема не решается)
    mask = mkb.parent_id.isna()
    level = 0
    while True:
        df = mkb[mask].copy()

        if len(df) == 0:
            break

        df["level"] = level
        values = get_list_of_tuples(df[["id", "code", "name", "parent_id", "level"]])

        query = """
        INSERT INTO mkb (
            id, code, name, parent_id, level
        )
        VALUES %s;
        """
        with conn:
            with conn.cursor() as cur:
                execute_values(cur, query, values)

        level += 1
        mask = mkb.parent_id.isin(df.id)  # Идем на следующий уровень


def import_referral_headers(data, conn):
    data = data[["referral_id", "db_patient_id", "db_diagnosis_id"]]
    data = data.drop_duplicates()
    values = get_list_of_tuples(data)

    query = "INSERT INTO referral_header (import_id, patient_id, diagnosis_id) VALUES %s;"
    with conn:
        with conn.cursor() as cur:
            execute_values(cur, query, values)


def import_referral_bodies(data, conn):
    data = data[
        [
            "db_referral_header_id",
            "sampling_date",
            "db_test_id",
            "result",
            "age_when_sampling",
        ]
    ]
    data = data.drop_duplicates()
    values = get_list_of_tuples(data)

    query = """
INSERT INTO referral_body (
    referral_header_id,
    sampling_date,
    test_id,
    result,
    patient_age_when_sampling)
VALUES %s;
"""
    with conn:
        with conn.cursor() as cur:
            execute_values(cur, query, values)


def get_db_patient_id(data, conn):
    sql = "SELECT id, import_id FROM patient;"
    with conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            result = cur.fetchall()

    db_df = pd.DataFrame(result, columns=["db_patient_id", "db_patient_import_id"])
    db_df["db_patient_id"] = db_df["db_patient_id"].astype("int")
    merged = pd.merge(
        data,
        db_df,
        left_on="patient_id",
        right_on="db_patient_import_id",
        how="left",
    )
    merged.drop(columns="db_patient_import_id", inplace=True)
    return merged


def get_db_test_id(data, conn):
    sql = "SELECT id, name FROM test;"
    with conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            result = cur.fetchall()

    db_df = pd.DataFrame(result, columns=["db_test_id", "db_test_name_id"])
    merged = pd.merge(
        data,
        db_df,
        left_on="ref_test_name",
        right_on="db_test_name_id",
        how="left",
    )
    merged.drop(columns="db_test_name_id", inplace=True)
    merged.dropna(subset="db_test_id", inplace=True)
    merged["db_test_id"] = merged["db_test_id"].astype("int")
    return merged


def get_db_diagnosis_id(data, conn):
    sql = "SELECT id, code FROM mkb;"
    with conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            result = cur.fetchall()

    db_df = pd.DataFrame(result, columns=["db_diagnosis_id", "diagnosis_code"])
    merged = pd.merge(
        data,
        db_df,
        on="diagnosis_code",
        how="left",
    )
    merged.dropna(subset="db_diagnosis_id", inplace=True)
    merged["db_diagnosis_id"] = merged["db_diagnosis_id"].astype("int")
    return merged


def get_db_referral_header_id(data, conn):
    sql = "SELECT id, import_id FROM referral_header;"
    with conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            result = cur.fetchall()

    db_df = pd.DataFrame(
        result, columns=["db_referral_header_id", "db_referral_header_import_id"]
    )
    db_df["db_referral_header_id"] = db_df["db_referral_header_id"].astype("str")
    db_df["db_referral_header_import_id"] = db_df["db_referral_header_import_id"].astype(
        "str"
    )
    merged = pd.merge(
        data,
        db_df,
        left_on="referral_id",
        right_on="db_referral_header_import_id",
        how="left",
    )
    merged.drop(columns="db_referral_header_import_id", inplace=True)
    return merged


def main():
    print("Loading analysis reference... ", end="", flush=True)
    reference = load_reference()
    print("done")

    print("Loading data [1/2] (kondinsky)... ", end="", flush=True)
    kondinsky = load_kondinsky()
    kondinsky = preprocess_district_data(
        kondinsky,
        kondinsky_rename_dict,
        reference,
        "kondinsky_both_test_name",
        KONDINSKY_PREFIX,
        kondinsky_date_converter,
        "Кодинский район",
    )
    print("done")

    print("Loading data [2/2] (ishim)... ", end="", flush=True)
    ishim = load_ishim()
    ishim = preprocess_district_data(
        ishim,
        ishim_rename_dict,
        reference,
        "ishim_test_name",
        ISHIM_PREFIX,
        ishim_date_converter,
        "Ишимский район",
    )
    print("done")

    print("Unioning data... ", end="", flush=True)
    data = pd.concat([kondinsky, ishim])
    print("done")

    print("Preprocessing united data... ", end="", flush=True)
    preprocess_united_data_inplace(data)
    print("done")

    conn = pg.connect(
        dbname=config["DB_NAME"],
        user=config["DB_USER"],
        password=config["DB_PASSWORD"],
    )

    print("Importing districts... ", end="", flush=True)
    import_districts(data, conn)
    print("done")

    print("Importing patients... ", end="", flush=True)
    import_patients(data, conn)
    print("done")

    print("Getting patient id from db... ", end="", flush=True)
    data = get_db_patient_id(data, conn)
    print("done")

    print("Importing analysis... ", end="", flush=True)
    import_analysis(data, conn)
    print("done")

    print("Importing tests... ", end="", flush=True)
    import_tests(data, conn)
    print("done")

    print("Getting test id from db... ", end="", flush=True)
    data = get_db_test_id(data, conn)
    print("done")

    print("Importing mkb... ", end="", flush=True)
    import_mkb(conn)
    print("done")

    print("Getting diagnosis id from db... ", end="", flush=True)
    data = get_db_diagnosis_id(data, conn)
    print("done")

    print("Importing referral headers... ", end="", flush=True)
    import_referral_headers(data, conn)
    print("done")

    print("Getting referral header id from db... ", end="", flush=True)
    data = get_db_referral_header_id(data, conn)
    print("done")

    print("Importing referral bodies... ", end="", flush=True)
    import_referral_bodies(data, conn)
    print("done")


if __name__ == "__main__":
    main()
