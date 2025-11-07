import common
import pandas as pd
from psycopg2.extras import RealDictCursor

GENDER_MALE = "м"
GENDER_FEMALE = "ж"


def get_result_as_df(connection, query, params=None):
    with connection.cursor() as cur:
        cur.execute(query, params)
        result = cur.fetchall()
        col_names = [desc[0] for desc in cur.description]

    return pd.DataFrame(result, columns=col_names)


def get_result_list_of_dicts(connection, query, params=None):
    with connection.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query)
        result = cur.fetchall()

    return result


def get_tests(connection):
    query = """
WITH cte AS (
	SELECT t.id, count(*) AS count
	FROM referral_body AS rb
	JOIN test AS t
	ON rb.test_id = t.id
	GROUP BY t.id
)
SELECT cte.id, t.name, cte.count, a.name AS analysis_name
FROM cte
JOIN test AS t
ON t.id  = cte.id
JOIN analysis AS a
ON a.id  = t.analysis_id
ORDER BY cte.count DESC;
"""
    return get_result_list_of_dicts(connection, query)


def get_diagnoses(connection):
    query = """
WITH cte AS (
    SELECT
        diagnosis_id,
        count(*) AS count
    FROM referral_header
    GROUP BY diagnosis_id
)
SELECT
    mkb.id,
    mkb.code,
    mkb.name,
    mkb.parent_id,
    mkb.level,
    cte.count
FROM cte
RIGHT JOIN mkb ON cte.diagnosis_id = mkb.id
ORDER BY mkb.parent_id, mkb.code;
"""
    return get_result_as_df(connection, query)


def get_associated_diagnoses(connection, patient_ids):
    query = """
SELECT
    m.code, m.name, count(*) AS count
FROM
    referral_header AS rh
JOIN mkb AS m ON
    m.id = rh.diagnosis_id
WHERE
    rh.patient_id IN %(patient_ids)s
GROUP BY
    m.code, m.name;
"""
    params = {"patient_ids": tuple(patient_ids)}

    return get_result_as_df(connection, query, params)


def get_dataset(connection, sample_filter, test_ids=None):
    query = """
SELECT
	rb.referral_header_id,
    rh.patient_id,
    rh.diagnosis_id,
	t.id AS "test_id",
	t.name AS "test_name",
	t.mnemonic AS "test_mnemonic",
	rb.sampling_date,
	rb.result,
	rb.patient_age_when_sampling,
	p.gender,
    p.district_id
FROM referral_body AS rb
JOIN test AS t              ON rb.test_id = t.id
JOIN referral_header AS rh  ON rb.referral_header_id = rh.id
JOIN patient AS p           ON rh.patient_id = p.id
WHERE
	rb.patient_age_when_sampling >= %(min_age)s
	AND	rb.patient_age_when_sampling <= %(max_age)s
	AND	rb.sampling_date >= %(min_sampling_date)s
 	AND rb.sampling_date <= %(max_sampling_date)s
"""
    params = {
        "min_age": sample_filter["age_interval"][0],
        "max_age": sample_filter["age_interval"][1],
        "min_sampling_date": sample_filter["sampling_date_interval"][0],
        "max_sampling_date": sample_filter["sampling_date_interval"][1],
    }

    if sample_filter["diagnoses"] != []:
        query += "AND rh.diagnosis_id IN %(diagnoses)s\n"
        params["diagnoses"] = tuple(sample_filter["diagnoses"])
    
    if sample_filter["district"] != [-1] and sample_filter["district"] != []:
        query += "AND p.district_id IN %(district)s\n"
        params["district"] = tuple(sample_filter["district"])

    if sample_filter["gender"] != "ANY":
        query += "AND p.gender = %(gender)s\n"
        params["gender"] = sample_filter["gender"]

    if test_ids is not None:
        if type(test_ids) == int:
            test_ids = [test_ids]
        query += "AND test_id IN %(test_ids)s\n"
        params["test_ids"] = tuple(test_ids)

    query += ";"

    return get_result_as_df(connection, query, params)
