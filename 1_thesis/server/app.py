import api
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)

CORS(app)

rules = [
    # Получение данных для списков
    ("/api/tests", api.get_tests, ["GET"]),
    ("/api/diagnoses", api.get_diagnoses, ["GET"]),
    # Описательные статистики
    ("/api/stats", api.get_stats, ["POST"]),
    # Изучение распределения
    ("/api/hist", api.get_hist, ["POST"]),
    ("/api/density", api.get_density, ["POST"]),
    ("/api/box", api.get_box, ["POST"]),
    ("/api/violin", api.get_violin, ["POST"]),
    # Изучение корреляции и многомерного распределения
    ("/api/scatter", api.get_scatter, ["POST"]),
    ("/api/hex", api.get_hex, ["POST"]),
    # Оценка статистических гипотез
    ("/api/ttest", api.get_ttest, ["POST"]),
    ("/api/mediantest", api.get_mediantest, ["POST"]),
    ("/api/oneway_anova", api.get_oneway_anova, ["POST"]),
    # Анализ скрытых закономерностей (data-mining)
    ("/api/hierarchy", api.get_hierarchy, ["POST"]),
    ("/api/kmeans", api.get_kmeans, ["POST"]),
]

for rule in rules:
    app.add_url_rule(rule=rule[0], view_func=rule[1], methods=rule[2])

if __name__ == "__main__":
    app.run(debug=True)
