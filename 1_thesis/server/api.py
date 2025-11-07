import base64
import io
import json
from pprint import pprint

import common
import numpy as np
import pandas as pd
import psycopg2 as pg
import seaborn as sns
import statsmodels.stats.multitest as multi
from dotenv import dotenv_values
from flask import Response, jsonify, request
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib
from pyclustering.cluster.center_initializer import kmeans_plusplus_initializer
from pyclustering.cluster.encoder import cluster_encoder
from pyclustering.cluster.kmeans import kmeans
from pyclustering.utils.metric import distance_metric
from scipy import stats as scipy_stats
from scipy.cluster.hierarchy import dendrogram
from sklearn.cluster import AgglomerativeClustering
from sklearn.decomposition import PCA
from sklearn.neighbors import LocalOutlierFactor


# https://json-schema.org/understanding-json-schema/index.html
from jsonschema import validate, exceptions

import db
import schemas

config = dotenv_values(common.ENV_FILE)

matplotlib.use("agg", force=True)

connection = pg.connect(
    dbname=config["DB_NAME"],
    user=config["DB_USER"],
    password=config["DB_PASSWORD"],
)


sns.set_palette("pastel")

dpi = 200
aspect_ratio = 1.66666
figure_height = 4  # inches
common_figure_size = (figure_height * aspect_ratio, figure_height)
square_figure_size = (figure_height, figure_height)

max_points_to_draw = 5000

gender_male_one_hot = "gender_м"
gender_female_one_hot = "gender_ж"

image_bytes = io.BytesIO()


def get_image_size(figure_size):
    return (figure_size[0] * dpi, figure_size[1] * dpi)


columns_translator = {
    "gender": "Пол",
    "patient_age_when_sampling": "Возраст",
    "result": "Результаты анализа",
    "cluster": "Кластер",
    "sample_number": "Номер выборки",
    "sample_name": "Название выборки",
}

dist_metrics = {
    "euclidean": 0,
    "euclidean_square": 1,
    "manhattan": 2,
    "chebyshev": 3,
    "minkowski": 4,
    "canberra": 5,
    "chi_square": 6,
    "gower": 7,
}


def to_json_response(obj, status=200):
    # По неизвестному ряду причин flask.jsonify не работает как нужно
    json_str = json.dumps(obj, ensure_ascii=False)
    return Response(
        json_str,
        mimetype="application/json",
        status=status,
    )


def get_image_content(content_name, figure):
    return {
        "name": content_name,
        "type": "image",
        "value": figure_to_base64(figure),
    }


def figure_to_base64(figure):
    figure.savefig(image_bytes, format="png", bbox_inches="tight", dpi=dpi)
    image_bytes.seek(0)
    return base64.b64encode(image_bytes.getvalue()).decode("utf-8")


def get_table_content(content_name, table, title):
    if isinstance(table, pd.DataFrame):
        # records: list like [{column -> value}, … , {column -> value}]
        table = table.to_dict("records")
    elif isinstance(table, dict):
        table = [table]
    else:
        raise ValueError("Table object has wrong type.")

    return {
        "name": content_name,
        "type": "table",
        "value": {
            "title": title,
            "table": table,
        },
    }

error_text = { 
    0: "В выбранной(ых) выборке(ах) имеется 0 записей",
    1: "В запросе не были указаны все необходимые параметры или параметры указаны в некорректном формате",
    2: "В запросе должны быть указаны минимум две выборки",
    999: "Unknown Error",
}

def get_error_content(error_code):
    return {
        "name": f"{error_code:03}",
        "type": "error",
        "value": error_text[error_code],
    }

def params_validate(params, schema):
    try: validate(params, schema)
    except Exception as e:
        print(e)
        content = get_error_content(1)
        return to_json_response([content])
    return 0

def get_df(connection, params, pivot=False, pivot_columns="test_name"):
    # connection = connection, duh
    # params = json / dict parameters for samples (sample(s) and test_id(s) specificaly)
    # pivot = bool value, true if pivoting df is required
    # pivot_column = which column name is left in the resulting df ("test_name" or "test_id")
    if "test_id" in params: test_id_ = params["test_id"]
    elif "test_id1" in params: test_id_ = [params["test_id1"], params["test_id2"]]
    elif "test_ids" in params: test_id_ = params["test_ids"]

    if "samples" in params:
        res = []
        for sample in params["samples"]:
            df = db.get_dataset(connection, sample, test_id_)
            if pivot:
                df = (
                    df
                    .drop_duplicates(["referral_header_id", "test_id"])
                    .pivot(
                        index=["referral_header_id", "gender", "patient_age_when_sampling"],
                        columns=pivot_columns,
                        values="result",
                    )
                    .dropna()
                    .rename(columns=columns_translator)
                )
            res.append(df)
    elif "sample" in params:
        res = db.get_dataset(connection, params["sample"], test_id_)
        if pivot:
            res = (
                res
                .drop_duplicates(["referral_header_id", "test_id"])
                .pivot(
                    index=["referral_header_id", "gender", "patient_age_when_sampling"],
                    columns=pivot_columns,
                    values="result",
                )
                .dropna()
                .rename(columns=columns_translator)
            )
    
    if (isinstance(res, pd.DataFrame) and len(res)==0) or (isinstance(res, list) and any([len(_)==0 for _ in res])==True):
        content = get_error_content(0)
        return to_json_response([content])
    
    return res


### Заполнение выпадающих списков ###


def get_tests():
    return to_json_response(db.get_tests(connection))


def get_diagnoses():
    df = db.get_diagnoses(connection)

    df["parent_id"] = df["parent_id"].fillna(-1).astype("int")
    root_group = pd.DataFrame(
        {
            "id": -1,
            "parent_id": -2,
            "level": -1,
            "name": "Все диагнозы",
            "count": 0,
            "code": "",
        },
        index=[len(df)],
    )
    df = pd.concat([df, root_group], copy=False)

    df["count"] = df["count"].fillna(0).astype("int")
    df["group_count"] = df["count"]

    df.set_index("id", drop=False, inplace=True)
    df.index.name = ""

    levels = sorted(df.level.unique(), reverse=True)
    levels.remove(-1)
    for level in levels:
        sums = df[df.level == level].groupby("parent_id")["count"].agg("sum")
        df.loc[sums.index, "count"] = df.loc[sums.index, "count"] + sums

    df.sort_values(["level", "count"], ascending=False, inplace=True)

    return to_json_response(df.to_dict("records"))


### Описательные статистики ###


def q25(x):
    return x.quantile(0.25)


def q50(x):
    return x.quantile(0.50)


def q75(x):
    return x.quantile(0.75)


functions = ["count", "min", q25, q50, q75, "max", "mean", "std"]


# cn - "column name" (in df)
def get_test_stats(df, group_creator_cn, group_content_cn, value_cn):
    results = []
    for group in df[group_creator_cn].unique():
        filtered_df = df[df[group_creator_cn] == group]

        stats_df = filtered_df.groupby(group_content_cn)[value_cn].aggregate(functions)
        stats_df.fillna(0, inplace=True)
        stats_df.reset_index(names="row_name", inplace=True)

        results.append(dict(df=stats_df, title=f"Описательные статистики — {group}"))

    return results


def get_gender_stats(df, sample_cn, gender_cn):
    rows = []
    sample_names = df[sample_cn].unique()
    for sample_name in sample_names:
        filtered_df = df[df[sample_cn] == sample_name]
        counts = filtered_df[gender_cn].value_counts()
        row = counts.to_dict()
        row["count_total"] = counts.sum()
        rows.append(row)
    stats_df = pd.DataFrame(rows, index=sample_names)
    stats_df.fillna(0, inplace=True)
    stats_df.reset_index(names="row_name", inplace=True)
    stats_df.rename(columns={"м": "count_male", "ж": "count_female"}, inplace=True)
    return dict(df=stats_df, title="Описательные статистики — Пол")


def get_age_stats(df, sample_cn, age_cn):
    stats_df = df.groupby(sample_cn)[age_cn].aggregate(functions)
    stats_df.fillna(0, inplace=True)
    stats_df.reset_index(names="row_name", inplace=True)
    return dict(df=stats_df, title="Описательные статистики — Возраст")


def get_stats():
    params = request.json
    valid = params_validate(params, schemas.stats)
    if valid != 0: return valid # now valid is an error message

    dfs = get_df(connection, params)
    if isinstance(dfs, Response): return dfs # now df is an error message

    for i in range(len(dfs)):
        dfs[i]["sample_name"] = params["samples"][i]["name"]

    united_df = pd.concat(dfs)

    if params["group_by"] == "samples":
        group_creator_cn = "sample_name"
        group_content_cn = "test_name"
    elif params["group_by"] == "params":
        group_creator_cn = "test_name"
        group_content_cn = "sample_name"

    content_list = []

    test_stats = get_test_stats(
        united_df,
        group_creator_cn,
        group_content_cn,
        "result",
    )
    content_list += [
        get_table_content("test_stats", stats["df"], stats["title"])
        for stats in test_stats
    ]

    if params["calc_gender_stats"]:
        gender_stats = get_gender_stats(
            united_df,
            "sample_name",
            "gender",
        )
        content_list.append(
            get_table_content("gender_stats", gender_stats["df"], gender_stats["title"])
        )

    if params["calc_age_stats"]:
        age_stats = get_age_stats(
            united_df,
            "sample_name",
            "patient_age_when_sampling",
        )
        content_list.append(
            get_table_content("age_stats", age_stats["df"], age_stats["title"])
        )

    return to_json_response(content_list)


### Изучение распределения ###


def get_hist():
    params = request.json
    valid = params_validate(params, schemas.hist)
    if valid != 0: return valid

    df = get_df(connection, params)
    if isinstance(df, Response): return df

    col = df["result"]
    df = df[np.abs(scipy_stats.zscore(col)) < params["z_value"]]

    df.rename(columns=columns_translator, inplace=True)

    figure = Figure(figsize=common_figure_size)
    ax = figure.add_subplot(1, 1, 1)
    ax.set_title("Гистограмма распределения")

    sns.histplot(
        df,
        x=columns_translator["result"],
        bins=params["bins"],
        kde=params["density"],
        ax=ax,
    ).set(ylabel="Частота")

    content = get_image_content("hist", figure)
    return to_json_response([content])


def get_density():
    params = request.json
    valid = params_validate(params, schemas.density)
    if valid != 0: return valid

    df = get_df(connection, params, pivot=True)
    if isinstance(df, Response): return df

    df = df[np.abs(scipy_stats.zscore(df.iloc[:, -1])) < params["z_value"]]

    figure = Figure(figsize=common_figure_size)
    ax = figure.add_subplot(1, 1, 1)
    ax.set_title("График плотности")

    sns.kdeplot(df, ax=ax).set(ylabel="Плотность")

    content = get_image_content("density", figure)
    return to_json_response([content])


def get_box():
    params = request.json
    valid = params_validate(params, schemas.box_violin)
    if valid != 0: return valid

    dfs = get_df(connection, params)
    if isinstance(dfs, Response): return dfs

    for i in range(len(dfs)):
        col = dfs[i]["result"]
        dfs[i] = dfs[i][np.abs(scipy_stats.zscore(col)) < params["z_value"]]

    for i in range(len(dfs)):
        dfs[i]["sample_name"] = params["samples"][i]["name"]

    final_df = pd.concat(dfs)
    final_df.rename(columns=columns_translator, inplace=True)

    figure = Figure(figsize=common_figure_size)
    ax = figure.add_subplot(1, 1, 1)
    ax.set_title("Ящичная диаграмма")

    sns.boxplot(
        data=final_df,
        x=columns_translator["sample_name"],
        y=columns_translator["result"],
        ax=ax,
    )

    content = get_image_content("box", figure)
    return to_json_response([content])


def get_violin():
    params = request.json
    valid = params_validate(params, schemas.box_violin)
    if valid != 0: return valid

    dfs = get_df(connection, params)
    if isinstance(dfs, Response): return dfs
    
    for i in range(len(dfs)):
        col = dfs[i]["result"]
        dfs[i] = dfs[i][np.abs(scipy_stats.zscore(col)) < params["z_value"]]

    for i in range(len(dfs)):
        dfs[i]["sample_name"] = params["samples"][i]["name"]

    final_df = pd.concat(dfs)
    final_df.rename(columns=columns_translator, inplace=True)

    figure = Figure(figsize=common_figure_size)
    ax = figure.add_subplot(1, 1, 1)
    ax.set_title("Скрипичная диаграмма")

    sns.violinplot(
        data=final_df,
        x=columns_translator["sample_name"],
        y=columns_translator["result"],
        ax=ax,
    )

    content = get_image_content("violin", figure)
    return to_json_response([content])


### Изучение корреляции и многомерного распределения ###


def get_scatter():
    params = request.json
    valid = params_validate(params, schemas.scatter_hex)
    if valid != 0: return valid

    df = get_df(connection, params, pivot=True)
    if isinstance(df, Response): return df

    df = df[np.abs(scipy_stats.zscore(df.iloc[:, 0])) < params["z_value"]]
    df = df[np.abs(scipy_stats.zscore(df.iloc[:, 1])) < params["z_value"]]

    figure = Figure(figsize=square_figure_size)
    ax = figure.add_subplot(1, 1, 1)
    ax.set_title("Диаграмма рассеяния")

    sns.scatterplot(
        df,
        x=df.columns[1],
        y=df.columns[0],
        ax=ax,
        size=[1] * len(df),
        sizes=(10, 10),
        legend=False,
    )

    content = get_image_content("scatter", figure)
    return to_json_response([content])


def get_hex():
    params = request.json
    valid = params_validate(params, schemas.scatter_hex)
    if valid != 0: return valid

    df = get_df(connection, params, pivot=True)
    if isinstance(df, Response): return df

    df = df[np.abs(scipy_stats.zscore(df[df.columns[-2]])) < params["z_value"]]
    df = df[np.abs(scipy_stats.zscore(df[df.columns[-1]])) < params["z_value"]]

    figure = sns.jointplot(
        df,
        x=df.columns[-2],
        y=df.columns[-1],
        kind="hex",
        height=figure_height,
    ).figure

    figure.suptitle("Сетка шестиугольников", y=1)

    content = get_image_content("hex", figure)
    return to_json_response([content])


### Проверка статистических гипотез ###


def get_ttest():
    params = request.json

    res = {}
    if params["ttest_type"] == 0:
        valid = params_validate(params, schemas.ttest0)
        if valid != 0: return valid

        df = get_df(connection, params, pivot=True, pivot_columns="test_id")
        if isinstance(df, Response): return df

        pr_res = scipy_stats.pearsonr(df[params["test_id1"]], df[params["test_id2"]])
        null_hypothesis = True if pr_res.pvalue < params["threshold"] else False
        # pvalue = probability that abs(r') of a random sample x' and y'
        # drawn from the population with zero correlation would be
        # greater than or equal to abs(r). BASICALLY: SMALLER pvalue = BETTER
        qvalue = multi.multipletests(pr_res.pvalue, alpha=params["threshold"])
        # qvalue = adjusted p values, supposedly it's better and accounts for false positives errors
        res = {
            "stats": pr_res.statistic,
            "pvalue": pr_res.pvalue,
            "pvalue_null_h": null_hypothesis,
            "qvalue": qvalue[1][0],
            "qvalue_null_h": bool(qvalue[0][0]),
        }

    if params["ttest_type"] == 1:
        valid = params_validate(params, schemas.ttest1)
        if valid != 0: return valid

        df = get_df(connection, params, pivot=True)
        if isinstance(df, Response): return df

        tt_res = scipy_stats.ttest_1samp(df, params["value"])
        null_hypothesis = True if tt_res.pvalue > params["threshold"] else False
        # statistic = positive if sample (data1) mean > given population mean (data2)
        # and statistic = negative if <
        # if p-value > chosen threshold (e.g. 1% or 5%) then
        # null hypothesis that the data1 mean == data2 is not rejected
        qvalue = multi.multipletests(tt_res.pvalue, alpha=params["threshold"])
        res = {
            "stats": float(tt_res.statistic),
            "pvalue": float(tt_res.pvalue),
            "pvalue_null_h": null_hypothesis,
            "qvalue": qvalue[1][0],
            "qvalue_null_h": not qvalue[0][0],
        }

    if params["ttest_type"] == 2:
        valid = params_validate(params, schemas.ttest2)
        if valid != 0: return valid

        params["sample"] = params["sample1"]
        df1 = get_df(connection, params, pivot=True)
        if isinstance(df1, Response): return df1

        params["sample"] = params["sample2"]
        df2 = get_df(connection, params, pivot=True)
        if isinstance(df2, Response): return df2

        # equal_var:
        # true = standard t-test w/ equal population variances
        # false = Welch’s t-test w/o equal population variance
        tt_res = scipy_stats.ttest_ind(df1, df2, equal_var=False)
        null_hypothesis = [
            True if p > params["threshold"] else False for p in tt_res.pvalue
        ]
        # pvalue = determined by comparing the t-statistic of the observed data
        # against a theoretical t-distribution
        # if p-value > chosen threshold then null hypothesis of equal population means is not rejected
        qvalue = multi.multipletests(tt_res.pvalue, alpha=params["threshold"])
        res = {
            "row_name": df1.columns,
            "stats": list(tt_res.statistic),
            "pvalue": list(tt_res.pvalue),
            "pvalue_null_h": null_hypothesis,
            "qvalue": list(qvalue[1]),
            "qvalue_null_h": [not _ for _ in qvalue[0]],
        }
    
    if isinstance(res["pvalue_null_h"], bool):
        res["pvalue_null_h"] = "не отвергается" if res["pvalue_null_h"]==True else "отвергается"
        res["qvalue_null_h"] = "не отвергается" if res["qvalue_null_h"]==True else "отвергается"
    else: 
        res["pvalue_null_h"] = list(map(lambda _: "не отвергается" if _==True else "отвергается", res["pvalue_null_h"]))
        res["qvalue_null_h"] = list(map(lambda _: "не отвергается" if _==True else "отвергается", res["qvalue_null_h"]))
        res = pd.DataFrame.from_dict(res)
    
    content_list = [get_table_content("ttest_stats", res, "Результаты t-статистики")]
    return content_list


def get_mediantest():
    params = request.json
    valid = params_validate(params, schemas.mediantest)
    if valid != 0: return valid
    # minimum 2 samples 
    if len(params["samples"]) < 2: return to_json_response([get_error_content(2)])
    
    dfs = get_df(connection, params, pivot=True)
    if isinstance(dfs, Response): return dfs
    for _ in range(len(dfs)):
        dfs[_] = dfs[_].values.flatten()

    mt_res = scipy_stats.median_test(*dfs)
    chi, chi_crit = mt_res.statistic, scipy_stats.chi2.ppf(
        1 - params["threshold"], df=1
    )  # ppf(1-threshold, degrees of freedom=num_of_arrays-1)
    res = {
        "median": mt_res.median,
        "chi": chi,
        "chi_crit": chi_crit,
        "null_h": "не отвергается" if chi < chi_crit else "отвергается",
    }
    
    content_list = [get_table_content("mediantest_stats", res, "Результаты медианного критерия")]
    return content_list


def get_oneway_anova():
    params = request.json
    valid = params_validate(params, schemas.oneway_anova)
    if valid != 0: return valid
    # minimum 2 samples 
    if len(params["samples"]) < 2: return to_json_response([get_error_content(2)])

    dfs = get_df(connection, params, pivot=True)
    if isinstance(dfs, Response): return dfs

    owa_res = scipy_stats.f_oneway(*dfs)
    null_hypothesis = [True if p > params["threshold"] else False for p in owa_res.pvalue]
    qvalue = multi.multipletests(owa_res.pvalue, alpha=params["threshold"])
    # the 'false' in h_null implies that we have sufficient proof to say
    # that there exists a difference in that column's values
    res = {
        "row_name": dfs[0].columns,
        "stats": list(owa_res.statistic),
        "pvalue": list(owa_res.pvalue),
        "pvalue_null_h": null_hypothesis,
        "qvalue": list(qvalue[1]),
        "qvalue_null_h": [not _ for _ in qvalue[0]],
    }
    res["pvalue_null_h"] = list(map(lambda _: "не отвергается" if _==True else "отвергается", res["pvalue_null_h"]))
    res["qvalue_null_h"] = list(map(lambda _: "не отвергается" if _==True else "отвергается", res["qvalue_null_h"]))
    res = pd.DataFrame.from_dict(res)
    
    content_list = [get_table_content("owa_stats", res, "Результаты однофакторного дисперсионного анализа")]
    return content_list


### Анализ скрытых закономерностей (data-mining) ###


def get_kmeans():
    params = request.json
    valid = params_validate(params, schemas.kmeans)
    if valid != 0: return valid

    dfs = get_df(connection, params)
    if isinstance(dfs, Response): return dfs

    df = pd.concat(dfs)
    df.drop_duplicates(["referral_header_id", "test_name"], inplace=True)
    pivot_df = (
        df
        .pivot(
            index=["referral_header_id", "gender", "patient_age_when_sampling"],
            columns="test_name",
            values="result",
        )
        .dropna()
        .reset_index(["gender", "patient_age_when_sampling"])
    )
    for _ in pivot_df.columns:
        if _!="gender": pivot_df = pivot_df[np.abs(scipy_stats.zscore(pivot_df[_])) < params["z_value"]]
    pivot_df = pd.get_dummies(pivot_df, columns=["gender"])

    splom_figure, stats = clust_kmeans(
        df, pivot_df, params["cluster_count"], params["dist_metric"]
    )

    splom_content = get_image_content("splom", splom_figure)

    return to_json_response([splom_content] + stats)


def clust_kmeans(original_df, pivot_df, cluster_count, dist_metric):
    norm_df = pivot_df.copy()
    for _ in norm_df.columns: norm_df[_] = scipy_stats.zscore(norm_df[_])
    
    init_centers = kmeans_plusplus_initializer(norm_df, cluster_count).initialize()
    metric = distance_metric(dist_metrics[dist_metric])
    model = kmeans(norm_df, initial_centers=init_centers, metric=metric)
    model.process()

    encoder = cluster_encoder(
        model.get_cluster_encoding(), model.get_clusters(), pivot_df
    )
    pivot_df["cluster"] = encoder.set_encoding(0).get_clusters()
    pivot_df["cluster"] += 1
    
    elems_to_draw = min(pivot_df.shape[0], 1000)
    df_to_draw = pivot_df.sample(elems_to_draw)
    df_to_draw.rename(columns=columns_translator, inplace=True)
    if gender_male_one_hot in df_to_draw.columns: df_to_draw.drop(columns=[gender_male_one_hot], inplace=True)
    if gender_female_one_hot in df_to_draw.columns: df_to_draw.drop(columns=[gender_female_one_hot], inplace=True)

    splom_figure = sns.pairplot(
        df_to_draw, hue=columns_translator["cluster"], palette="pastel"
    ).figure
    splom_figure.suptitle("Матрица сравнения кластеров", y=1)

    stats = get_clusters_stats(original_df, pivot_df)

    return splom_figure, stats


def get_clusters_stats(original_df, pivot_df):
    cluster_df = pd.merge(
        left=original_df,
        left_on="referral_header_id",
        right=pivot_df,
        right_index=True,
        how="inner",
    )

    cluster_df["cluster"] = "Кластер " + cluster_df["cluster"].astype("string")

    content_list = []

    # content_list.append(content)

    cluster_df.sort_values("cluster", inplace=True)

    test_stats = get_test_stats(cluster_df,  "test_name", "cluster","result")
    content_list += [
        get_table_content("test_stats", stats["df"], stats["title"])
        for stats in test_stats
    ]

    gender_stats = get_gender_stats(cluster_df, "cluster", "gender")
    content_list.append(
        get_table_content("gender_stats", gender_stats["df"], gender_stats["title"])
    )

    age_stats = get_age_stats(cluster_df, "cluster", "patient_age_when_sampling_x")
    content_list.append(
        get_table_content("age_stats", age_stats["df"], age_stats["title"])
    )

    assoc_diags = get_associated_diagnoses(cluster_df)
    content_list.append(
        get_table_content(
            "associated_diagnoses",
            assoc_diags,
            "Ассоциированные диагнозы (объединенные 10 самых популярных с каждого кластера)",
        )
    )

    return content_list


def get_associated_diagnoses(cluster_df):
    dfs = []
    i = 1
    for c in cluster_df["cluster"].unique():
        filter = cluster_df["cluster"] == c
        filtered_df = cluster_df[filter]
        patient_ids = filtered_df["patient_id"].unique().tolist()
        asd = db.get_associated_diagnoses(connection, patient_ids)
        asd["cluster"] = f"cluster{i}"
        dfs.append(asd.sort_values("count", ascending=False).head(10))
        i += 1

    df = pd.concat(dfs)
    pivot = pd.pivot(df, index="name", columns="cluster", values="count")
    pivot.fillna(0, inplace=True)
    pivot.sort_values(list(pivot.columns), ascending=False, inplace=True)
    pivot.reset_index(names="row_name", inplace=True)

    return pivot


# def get_cluster_box(cluster_df):
#     df = cluster_df.copy()

#     df.sort_values("test_name", inplace=True)

#     for t in df["test_name"].unique():
#         filter = (df["test_name"] == t)
#         df.loc[filter.index, t] =

#     for c in df["cluster"].unique():
#         filter = df["cluster"] == c
#         filtered_df = df[filter]

#         figure = Figure(figsize=common_figure_size)
#         ax = figure.add_subplot(1, 1, 1)
#         ax.set_title("Скрипичная диаграмма")

#         sns.violinplot(
#             data=filtered_df,
#             x="test_name",
#             y="result",
#             ax=ax,
#         )

#         content = get_image_content("violin", figure)


def get_hierarchy():
    params = request.json
    valid = params_validate(params, schemas.hierarchy)
    if valid != 0: return valid

    dfs = get_df(connection, params)
    if isinstance(dfs, Response): return dfs

    df = pd.concat(dfs)
    df.drop_duplicates(["referral_header_id", "test_name"], inplace=True)
    pivot_df = (
        df
        .drop_duplicates(["referral_header_id", "test_name"])
        .pivot(
            index=["referral_header_id", "gender", "patient_age_when_sampling"],
            columns="test_name",
            values="result",
        )
        .dropna()
        .reset_index(["gender", "patient_age_when_sampling"])
    )
    for _ in pivot_df.columns:
        if _!="gender": pivot_df = pivot_df[np.abs(scipy_stats.zscore(pivot_df[_])) < params["z_value"]]
    pivot_df = pd.get_dummies(pivot_df, columns=["gender"])

    dendrogram_figure, splom_figure, stats = clust_hierarchy(
        df, pivot_df, params["cluster_count"]
    )

    dendrogram_content = get_image_content("dendrogram", dendrogram_figure)
    splom_content = get_image_content("splom", splom_figure)

    return to_json_response([dendrogram_content, splom_content] + stats)


def clust_hierarchy(original_df, pivot_df, k):
    dendrogram_figure = clust_hierarchy_distance_threshold(
        pivot_df, truncate_mode="level", p=3
    )
    
    splom_figure, stats = clust_hierarchy_extract_clusters(
        pivot_df, original_df, k
    )

    return dendrogram_figure, splom_figure, stats


def clust_hierarchy_distance_threshold(pivot_df, dist=0, **kwargs):
    norm_df = pivot_df.copy()
    for _ in norm_df.columns: norm_df[_] = scipy_stats.zscore(norm_df[_])
    
    model = AgglomerativeClustering(n_clusters=None, distance_threshold=dist).fit(norm_df)
    dendrogram_figure = Figure(figsize=[12, 9])
    ax = dendrogram_figure.add_subplot(1, 1, 1)
    ax.set_xlabel(
        "Без скобок указывается индекс одного объекта, со скобками указывается кол-во объектов в группе"
    )

    # https://scikit-learn.org/stable/auto_examples/cluster/plot_agglomerative_dendrogram.html
    # create the counts of samples under each node
    counts = np.zeros(model.children_.shape[0])
    n_samples = len(model.labels_)
    for i, merge in enumerate(model.children_):
        current_count = 0
        for child_idx in merge:
            if child_idx < n_samples:
                current_count += 1  # leaf node
            else:
                current_count += counts[child_idx - n_samples]
        counts[i] = current_count

    linkage_matrix = np.column_stack([
        model.children_, 
        model.distances_, 
        counts
    ]).astype(float)

    # plot the corresponding dendrogram
    dendrogram(linkage_matrix, **kwargs, ax=ax)
    bytes = io.BytesIO()
    dendrogram_figure.savefig(bytes, format="png")
    # encoded_dendrogram = base64.b64encode(bytes.getvalue()).decode("ascii")

    return dendrogram_figure


def clust_hierarchy_extract_clusters(pivot_df, original_df, k):
    norm_df = pivot_df.copy()
    for _ in norm_df.columns: norm_df[_] = scipy_stats.zscore(norm_df[_])

    model = AgglomerativeClustering(n_clusters=k).fit(norm_df)
    pivot_df["cluster"] = model.labels_
    pivot_df["cluster"] += 1

    elems_to_draw = min(pivot_df.shape[0], 1000)
    df_to_draw = pivot_df.sample(elems_to_draw)
    df_to_draw.rename(columns=columns_translator, inplace=True)
    if gender_male_one_hot in df_to_draw.columns: df_to_draw.drop(columns=[gender_male_one_hot], inplace=True)
    if gender_female_one_hot in df_to_draw.columns: df_to_draw.drop(columns=[gender_female_one_hot], inplace=True)
    
    splom_figure = sns.pairplot(
        df_to_draw, hue=columns_translator["cluster"], palette="pastel"
    ).figure
    splom_figure.suptitle("Матрица сравнения кластеров", y=1)

    stats = get_clusters_stats(original_df, pivot_df)

    return splom_figure, stats


def lof(df):
    model = LocalOutlierFactor(n_neighbors=20, contamination=0.1)
    model.fit_predict(df)
    scores = model.negative_outlier_factor_  # lof scores

    # getting lowest 5 percent of score values as the anomalies
    threshold = np.quantile(scores, 0.05)
    anomalies = df.iloc[np.where(scores <= threshold)]

    return df.drop(anomalies.index)
