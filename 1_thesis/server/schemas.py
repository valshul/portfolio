sample = {
    "type": "object",
    "properties": {
        "age_interval": {
            "type": "array",
            "items": {"type": "integer"},
        },
        "sampling_date_interval": {
            "type": "array",
            "items": {"type": "string"},
        },
        "diagnoses": {
            "type": "array",
            "items": {"type": "integer"},
        },
        "district": {
            "type": "array",
            "items": {"type": "integer"},
        },
        "gender": {"enum": ["ANY", "м", "ж"]},
        "index": {"type": "integer"},
        "name": {"type": "string"},
    },
    "required": [
        "age_interval",
        "sampling_date_interval",
        "diagnoses",
        "district",
        "gender",
        "index",
    ],
}
samples = {
    "type": "array",
    "items": sample,
    "minItems": 1,
}

test_id = {"type": "integer"}
test_ids = {
    "type": "array",
    "items": test_id,
    "minItems": 1,
}

stats = {
    "type": "object",
    "properties": {
        "samples": samples,
        "test_ids": test_ids,
        "group_by": {"enum": ["samples", "params"]},
        "calc_gender_stats": {"type": "boolean"},
        "calc_age_stats": {"type": "boolean"},
    },
    "required": [
        "samples",
        "test_ids",
        "group_by",
        "calc_gender_stats",
        "calc_age_stats",
    ],
}

hist = {
    "type": "object",
    "properties": {
        "sample": sample,
        "test_id": test_id,
        "z_value": {"type": "number"},
        "bins": {"type": "integer"},
        "density": {"type": "boolean"},
    },
    "required": [
        "sample",
        "test_id",
        "z_value",
        "bins",
        "density",
    ],
}

density = {
    "type": "object",
    "properties": {
        "sample": sample,
        "test_id": test_id,
        "z_value": {"type": "number"},
    },
    "required": [
        "sample",
        "test_id",
        "z_value",
    ],
}

box_violin = {
    "type": "object",
    "properties": {
        "samples": samples,
        "test_id": test_id,
        "z_value": {"type": "number"},
    },
    "required": [
        "samples",
        "test_id",
        "z_value",
    ],
}

scatter_hex = {
    "type": "object",
    "properties": {
        "sample": sample,
        "test_id1": test_id,
        "test_id2": test_id,
        "z_value": {"type": "number"},
    },
    "required": [
        "sample",
        "test_id1",
        "test_id2",
        "z_value",
    ],
}

threshold = {
    "type": "number",
    "exclusiveMinimum": 0,
    "exclusiveMaximum": 1,
}
ttest0 = {
    "type": "object",
    "properties": {
        "ttest_type": {"type": "integer"},
        "sample": sample,
        "test_id1": test_id,
        "test_id2": test_id,
        "threshold": threshold,
    },
    "required": [
        "ttest_type",
        "sample",
        "test_id1",
        "test_id2",
        "threshold",
    ],
}
ttest1 = {
    "type": "object",
    "properties": {
        "ttest_type": {"type": "integer"},
        "sample": sample,
        "test_id": test_id,
        "value": {"type": "number"},
        "threshold": threshold,
    },
    "required": [
        "ttest_type",
        "sample",
        "test_id",
        "value",
        "threshold",
    ],
}
ttest2 = {
    "type": "object",
    "properties": {
        "ttest_type": {"type": "integer"},
        "sample1": sample,
        "sample2": sample,
        "test_ids": test_ids,
        "threshold": threshold,
    },
    "required": [
        "ttest_type",
        "sample1",
        "sample2",
        "test_ids",
        "threshold",
    ],
}

mediantest = {
    "type": "object",
    "properties": {
        "samples": samples,
        "test_id": test_id,
        "threshold": threshold,
    },
    "required": [
        "samples",
        "test_id",
        "threshold",
    ],
}

oneway_anova = {
    "type": "object",
    "properties": {
        "samples": samples,
        "test_ids": test_ids,
        "threshold": threshold,
    },
    "required": [
        "samples",
        "test_ids",
        "threshold",
    ],
}

kmeans = {
    "type": "object",
    "properties": {
        "samples": samples,
        "test_ids": test_ids,
        "cluster_count": {"type": "integer"},
        "dist_metric": {"type": "string"},
        "z_value": {"type": "number"},
    },
    "required": [
        "samples",
        "test_ids",
        "cluster_count",
        "dist_metric",
        "z_value",
    ],
}

hierarchy = {
    "type": "object",
    "properties": {
        "samples": samples,
        "test_ids": test_ids,
        "cluster_count": {"type": "integer"},
        "z_value": {"type": "number"},
    },
    "required": [
        "samples",
        "test_ids",
        "cluster_count",
        "z_value",
    ],
}
 