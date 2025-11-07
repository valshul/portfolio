import { useState, useCallback, useContext, useMemo } from "react";

import {
    Checkbox,
    Collapse,
    DatePicker,
    Image,
    InputNumber,
    Layout,
    Select,
    Typography,
} from "antd";
import { performRequest } from "Api";
import { getUniqueKey } from "Common";
import Table from "Table";
import { hints } from "Hints";

const { Panel } = Collapse;

const { Paragraph } = Typography;
const { RangePicker } = DatePicker;
const { Header, Footer, Sider, Content } = Layout;

// Enum
const Component = {
    Sample: 5,
    Samples: 10,
    Tests: 20,
    Test1: 30,
    Test2: 40,
    Bins: 50,
    Kde: 60,
    ZValue: 70,
    GroupBy: 80,
    CalcGenderStats: 90,
    CalcAgeStats: 100,
    ClusterCount: 110,
    DistanceMetric: 120,
    ExpectedMean: 130,
    Threshold: 140,
};

export default function Experiment({ experiment, tests, samples, showDeleteExperimentModal }) {
    const anyGenderString = "ANY";
    const maleGenderString = "м";
    const femaleGenderString = "ж";

    const sendingFormat = "YYYY-MM-DD";

    const [name, setName] = useState(
        `Исследование № ${experiment.index} — Пустой шаблон`
    );

    const [selectedExperiment, setSelectedExperiment] = useState();

    const [compSample, setCompSample] = useState();
    const [compSamples, setCompSamples] = useState();
    const [compBins, setCompBins] = useState(15);
    const [compUseKde, setCompUseKde] = useState(false);
    const [compZValue, setCompZValue] = useState(3);
    const [compTests, setCompTests] = useState();
    const [compTest1, setCompTest1] = useState();
    const [compTest2, setCompTest2] = useState();
    const [compGroupBy, setCompGroupBy] = useState();
    const [compCalcGenderStats, setCompCalcGenderStats] = useState(false);
    const [compCalcAgeStats, setCompCalcAgeStats] = useState(false);
    const [compClusterCount, setCompClusterCount] = useState(3);
    const [compDistanceMetric, setCompDistanceMetric] = useState("euclidean");
    const [compExpectedMean, setCompExpectedMean] = useState(0);
    const [compThreshold, setCompThreshold] = useState(0.05);

    const [componentsToRender, setComponentsToRender] = useState([]);

    const [result, setResult] = useState(<div></div>);

    const [activated, setActivated] = useState(experiment.activated);

    const samplesData = samples.map((s) => ({ label: s.name, value: s.index }));

    const experimentData = [
        {
            label: "Описательные статистики",
            options: [
                {
                    label: "Базовые описательные статистики",
                    value: "stats",
                    runFunction: runStats,
                    components: [
                        Component.Samples,
                        Component.Tests,
                        Component.GroupBy,
                        Component.CalcGenderStats,
                        Component.CalcAgeStats,
                    ],
                },
            ],
        },
        {
            label: "Изучение распределения",
            options: [
                {
                    label: "Гистограмма распределения",
                    value: "hist",
                    runFunction: runHist,
                    components: [
                        Component.Sample,
                        Component.Test1,
                        Component.Bins,
                        Component.ZValue,
                        Component.Kde,
                    ],
                },
                {
                    label: "График плотности",
                    value: "density",
                    runFunction: runDensity,
                    components: [Component.Sample, Component.Test1, Component.ZValue],
                },
                {
                    label: "Ящичная диаграмма",
                    value: "box",
                    runFunction: runBox,
                    components: [Component.Samples, Component.Test1, Component.ZValue],
                },
                {
                    label: "Скрипичная диаграмма",
                    value: "violin",
                    runFunction: runViolin,
                    components: [Component.Samples, Component.Test1, Component.ZValue],
                },
            ],
        },
        {
            label: "Изучение корреляции и многомерного распределения",
            options: [
                {
                    label: "Сетка шестиугольников",
                    value: "hex",
                    runFunction: runHex,
                    components: [
                        Component.Sample,
                        Component.Test1,
                        Component.Test2,
                        Component.ZValue,
                    ],
                },
                {
                    label: "Диаграмма рассеяния",
                    value: "scatter",
                    runFunction: runScatter,
                    components: [
                        Component.Sample,
                        Component.Test1,
                        Component.Test2,
                        Component.ZValue,
                    ],
                },
            ],
        },
        {
            label: "Оценка статистических гипотез",
            options: [
                {
                    label: "Оценка значимости коэффициента корреляции",
                    value: "ttest0",
                    runFunction: runTtest0,
                    components: [
                        Component.Sample,
                        Component.Test1,
                        Component.Test2,
                        Component.Threshold,
                    ],
                },
                {
                    label: "Сравнение генерального среднего с константой",
                    value: "ttest1",
                    runFunction: runTtest1,
                    components: [
                        Component.Sample,
                        Component.Test1,
                        Component.ExpectedMean,
                        Component.Threshold,
                    ],
                },
                {
                    label: "Сравнение средних значений двух независимых выборок",
                    value: "ttest2",
                    runFunction: runTtest2,
                    components: [
                        Component.Samples, // should be limitation EXACTLY 2 samples
                        Component.Tests,
                        Component.Threshold,
                    ],
                },
                {
                    label: "Медианный критерий",
                    value: "mediantest",
                    runFunction: runMediantest,
                    components: [
                        Component.Samples, // should be limitation MINIMUN 2 samples
                        Component.Test1,
                        Component.Threshold,
                    ],
                },
                {
                    label: "Однофакторный дисперсионный анализ",
                    value: "onewayanova",
                    runFunction: runOnewayanova,
                    components: [
                        Component.Samples, // should be limitation MINIMUM 2 samples
                        Component.Tests,
                        Component.Threshold,
                    ],
                },
            ],
        },
        {
            label: "Кластеризация",
            options: [
                {
                    label: "Метод k-средних",
                    value: "kmeans",
                    runFunction: runKMeans,
                    components: [
                        Component.Samples,
                        Component.Tests,
                        Component.ClusterCount,
                        Component.DistanceMetric,
                        Component.ZValue,
                    ],
                },
                {
                    label: "Иерархическая кластеризация",
                    value: "hierarchy",
                    runFunction: runHierarchy,
                    components: [
                        Component.Samples,
                        Component.Tests,
                        Component.ClusterCount,
                        Component.ZValue
                    ],
                },
            ],
        },
    ];

    const groupByOptions = [
        { value: "samples", label: "по выборке" },
        { value: "params", label: "по параметру" },
    ];

    const distanceMetricOptions = [
        { value: "euclidean", label: "Евклидово расстояние" },
        { value: "euclidean_square", label: "Квадрат евклидова расстояния" },
        { value: "manhattan", label: "Манхэттенское расстояние" },
        { value: "chebyshev", label: "Расстояние Чебышёва" },
        { value: "canberra", label: "Канберрское расстояние" },
        { value: "chi_square", label: "Расстояние хи-квадрат" },
    ];

    const testAndAgeColumns = [
        { accessor: "row_name", Header: "" },
        { accessor: "count", Header: "Кол-во", Cell: formatNumber },
        { accessor: "min", Header: "Мин.", Cell: formatNumber },
        { accessor: "q25", Header: "25-й проц.", Cell: formatNumber },
        { accessor: "q50", Header: "50-й проц.", Cell: formatNumber },
        { accessor: "q75", Header: "75-й проц.", Cell: formatNumber },
        { accessor: "max", Header: "Макс.", Cell: formatNumber },
        { accessor: "mean", Header: "Среднее", Cell: formatNumber },
        {
            accessor: "std",
            Header: "Ср. знач. откл.",
            Cell: formatNumber,
        },
    ];

    const genderColumns = [
        { accessor: "row_name", Header: "" },
        {
            accessor: "count_male",
            Header: "Кол-во мужчин",
            Cell: formatNumber,
        },
        {
            accessor: "count_female",
            Header: "Кол-во женщин",
            Cell: formatNumber,
        },
        { accessor: "count_total", Header: "Всего", Cell: formatNumber },
    ];
    const statHypothesisColumns = [
        { accessor: "stats", Header: "Статистика", Cell: formatNumber },
        { accessor: "pvalue", Header: "p-значение", Cell: formatNumber },
        { accessor: "pvalue_null_h", Header: "отвержение h0 на основе p-значения", Cell: formatNonZeroOrEmpty },
        { accessor: "qvalue", Header: "q-значение", Cell: formatNumber },
        { accessor: "qvalue_null_h", Header: "отвержение h0 на основе q-значения", Cell: formatNonZeroOrEmpty },
    ];

    function getExperimentByValue(expValue) {
        for (const exp of experimentData) {
            for (const opt of exp.options) {
                if (expValue === opt.value) {
                    return opt;
                }
            }
        }
    }

    function getTestByValue(testValue) {
        for (const test of tests) {
            for (const opt of test.options) {
                if (testValue === opt.value) {
                    return opt;
                }
            }
        }
    }

    function getSelectedSamples() {
        return samples.filter((s) => compSamples.includes(s.index));
    }

    function getSelectedSample() {
        for (const sample of samples) {
            if (sample.index == compSample) {
                return sample;
            }
        }
    }

    function getSampleRequestFromSample(sample) {
        try {
            let gender = "";
            if (sample.genderMale && sample.genderFemale) {
                gender = anyGenderString;
            } else if (sample.genderMale) {
                gender = maleGenderString;
            } else {
                gender = femaleGenderString;
            }
    
            let sampleRequest = {
                age_interval: sample.ageInterval,
                sampling_date_interval: [
                    sample.timeInterval[0].format(sendingFormat),
                    sample.timeInterval[1].format(sendingFormat),
                ],
                diagnoses: sample.diagnoses,
                district: sample.district,
                gender: gender,
                index: sample.index,
                name: sample.name,
            };

            return sampleRequest;
        }
        catch {return}
    }

    function getRenderParams(component) {
        // Grid, потому что такой стиль используется для instrument-settings-entry
        const visible = { display: "grid", visibility: "visible" };
        const hidden = { display: "none", visibility: "hidden" };
        if (componentsToRender.includes(component)) {
            return visible;
        } else {
            return hidden;
        }
    }

    function generateName() {
        const exp = getExperimentByValue(selectedExperiment);
        let experimentName = `Исследование №${experiment.index} — ${exp.label} (`
        
        try {
            if (exp.components.includes(Component.Samples)) {
                const samples = getSelectedSamples().map(sample => sample.name)
                experimentName += `выборки: ${samples}, `
            }
            else {
                const sample = getSelectedSample().name
                experimentName += `выборка: ${sample}, `
            }
        } catch (TypeError) {
            console.log("error: no sample data")
        }

        try {
            if (exp.components.includes(Component.Tests)) {
                const tests = compTests.map(testValue => getTestByValue(testValue).self.name)
                experimentName += `тесты: ${tests}`
            }
            else {
                if (exp.components.includes(Component.Test1)) {
                    const test1 = getTestByValue(compTest1).self.name
                    experimentName += `тест1: ${test1}`
                }
                if (exp.components.includes(Component.Test2)) {
                    const test2 = getTestByValue(compTest2).self.name
                    experimentName += `тест2: ${test2}`
                }
            }
        } catch (TypeError) {
            console.log("error: no test data")
        }

        return experimentName+`)`;
    }

    function renderContent(content, renderParams = null) {
        const key = getUniqueKey();
        switch (content.type) {
            case "image":
                const image = `data:image/png;charset=utf-8;base64,${content.value}`;
                return (
                    <div className="result-content" key={key}>
                        <Image className="image" alt="" src={image} />
                    </div>
                );

            case "table":
                const columns = renderParams[content.name].columns;
                return (
                    <div className="result-content" key={key}>
                        <Table
                            data={content.value.table}
                            columns={columns}
                            title={content.value.title}
                        />
                    </div>
                );
            case "error":
                return (
                    <div className="result-content" key={key}>
                        <div className="error">
                            {`Ошибка ${content.name}:`}
                            <br />
                            {content.value}
                        </div>
                    </div>
                );
            default:
                return <div>{"Нет контента"}</div>;
        }
    }

    function renderContentList(list, renderParams = null) {
        let contentList = list.map((x) => renderContent(x, renderParams));
        // Если будут картинки, то их можно будет листать в рамках одного исследования.
        // Если картинок не будет, то ничего страшного не произойдет
        contentList = <Image.PreviewGroup>{contentList}</Image.PreviewGroup>;
        setResult(contentList);
    }

    function formatNumber(obj) {
        // Объект с такой структурой (obj.cell.value) отправляет библиотека react-table
        obj = obj.cell.value;
        let res = obj;
        if (typeof obj == "number" && !Number.isInteger(obj)) {
            res = obj.toFixed(3);
        }
        return res;
    }

    function formatNonZeroOrEmpty(obj) {
        // Объект с такой структурой (obj.cell.value) отправляет библиотека react-table
        obj = obj.cell.value;
        let res = obj;
        if (typeof obj === "number" && obj === 0) {
            res = "";
        }
        return res;
    }

    function run() {
        setName(generateName());

        let exp = getExperimentByValue(selectedExperiment);
        exp.runFunction();
    }

    function runStats() {
        let samples = getSelectedSamples();
        let sampleRequests = samples.map((s) => getSampleRequestFromSample(s));

        let request = {
            test_ids: compTests,
            samples: sampleRequests,
            group_by: compGroupBy,
            calc_gender_stats: compCalcGenderStats,
            calc_age_stats: compCalcAgeStats,
        };

        (async () => {
            const contentList = await performRequest("post", "stats", request);

            const renderParams = {
                test_stats: { columns: testAndAgeColumns },
                age_stats: { columns: testAndAgeColumns },
                gender_stats: { columns: genderColumns },
            };

            renderContentList(contentList, renderParams);
        })();
    }

    function runHist() {
        let sample = getSelectedSample();

        let request = {
            test_id: compTest1,
            bins: compBins,
            z_value: compZValue,
            sample: getSampleRequestFromSample(sample),
            density: compUseKde,
        };

        (async () => {
            const contentList = await performRequest("post", "hist", request);
            renderContentList(contentList);
        })();
    }

    function runDensity() {
        let sample = getSelectedSample();

        let request = {
            test_id: compTest1,
            z_value: compZValue,
            sample: getSampleRequestFromSample(sample),
        };

        (async () => {
            const contentList = await performRequest("post", "density", request);
            renderContentList(contentList);
        })();
    }

    function runBox() {
        let samples = getSelectedSamples();
        let sampleRequests = samples.map((s) => getSampleRequestFromSample(s));

        let request = {
            test_id: compTest1,
            z_value: compZValue,
            samples: sampleRequests,
        };

        (async () => {
            const contentList = await performRequest("post", "box", request);
            renderContentList(contentList);
        })();
    }

    function runViolin() {
        let samples = getSelectedSamples();
        let sampleRequests = samples.map((s) => getSampleRequestFromSample(s));

        let request = {
            test_id: compTest1,
            z_value: compZValue,
            samples: sampleRequests,
        };

        (async () => {
            const contentList = await performRequest("post", "violin", request);
            renderContentList(contentList);
        })();
    }

    function runHex() {
        let sample = getSelectedSample();

        let request = {
            test_id1: compTest1,
            test_id2: compTest2,
            z_value: compZValue,
            sample: getSampleRequestFromSample(sample),
        };

        (async () => {
            const contentList = await performRequest("post", "hex", request);
            renderContentList(contentList);
        })();
    }

    function runScatter() {
        let sample = getSelectedSample();

        let request = {
            test_id1: compTest1,
            test_id2: compTest2,
            z_value: compZValue,
            sample: getSampleRequestFromSample(sample),
        };

        (async () => {
            const contentList = await performRequest("post", "scatter", request);
            renderContentList(contentList);
        })();
    }

    function runTtest0() {
        let sample = getSelectedSample();
        
        let request = {
            ttest_type: 0,
            test_id1: compTest1,
            test_id2: compTest2,
            threshold: compThreshold,
            sample: getSampleRequestFromSample(sample),
        };

        (async () => {
            const contentList = await performRequest("post", "ttest", request);

            const renderParams = {
                ttest_stats: { columns: statHypothesisColumns },
            };

            renderContentList(contentList, renderParams);
        })();
    }

    function runTtest1() {
        let sample = getSelectedSample();
        
        let request = {
            ttest_type: 1,
            test_id: compTest1,
            value: compExpectedMean,
            threshold: compThreshold,
            sample: getSampleRequestFromSample(sample),
        };

        (async () => {
            const contentList = await performRequest("post", "ttest", request);

            const renderParams = {
                ttest_stats: { columns: statHypothesisColumns },
            };

            renderContentList(contentList, renderParams);
        })();
    }

    function runTtest2() {
        let samples = getSelectedSamples();
        let sampleRequests = samples.map((s) => getSampleRequestFromSample(s));
        
        let request = {
            ttest_type: 2,
            test_ids: compTests,
            threshold: compThreshold,
            sample1: sampleRequests[0],
            sample2: sampleRequests[1],
        };

        (async () => {
            const contentList = await performRequest("post", "ttest", request);

            const renderParams = {
                ttest_stats: { columns: [{ accessor: "row_name", Header: "" }].concat(statHypothesisColumns) },
            };

            renderContentList(contentList, renderParams);
        })();
    }

    function runMediantest() {
        let samples = getSelectedSamples();
        let sampleRequests = samples.map((s) => getSampleRequestFromSample(s));
        
        let request = {
            test_id: compTest1,
            threshold: compThreshold,
            samples: sampleRequests,
        };

        (async () => {
            const contentList = await performRequest("post", "mediantest", request);

            const renderParams = {
                mediantest_stats: { columns: [
                    { accessor: "median", Header: "медиана", Cell: formatNumber },
                    { accessor: "chi", Header: "χ квадрат", Cell: formatNumber },
                    { accessor: "chi_crit", Header: "критическое χ квадрат", Cell: formatNumber },
                    { accessor: "null_h", Header: "отвержение h0", Cell: formatNonZeroOrEmpty },
                ]},
            };

            renderContentList(contentList, renderParams);
        })();
    }

    function runOnewayanova() {
        let samples = getSelectedSamples();
        let sampleRequests = samples.map((s) => getSampleRequestFromSample(s));
        
        let request = {
            test_ids: compTests,
            threshold: compThreshold,
            samples: sampleRequests,
        };

        (async () => {
            const contentList = await performRequest("post", "oneway_anova", request);

            const renderParams = {
                owa_stats: { columns: [{ accessor: "row_name", Header: "" }].concat(statHypothesisColumns) },
            };

            renderContentList(contentList, renderParams);
        })();
    }

    function runKMeans() {
        let samples = getSelectedSamples();
        let sampleRequests = samples.map((s) => getSampleRequestFromSample(s));

        let request = {
            test_ids: compTests,
            z_value: compZValue,
            cluster_count: compClusterCount,
            dist_metric: compDistanceMetric,
            samples: sampleRequests,
        };

        (async () => {
            const contentList = await performRequest("post", "kmeans", request);

            let associatedDiagnoses = [{ accessor: "row_name", Header: "Заболевание" }];
            for (let i = 1; i <= compClusterCount; i++) {
                associatedDiagnoses.push({
                    accessor: `cluster${i}`,
                    Header: `Кластер ${i}`,
                    Cell: formatNonZeroOrEmpty,
                });
            }

            const renderParams = {
                test_stats: { columns: testAndAgeColumns },
                age_stats: { columns: testAndAgeColumns },
                gender_stats: { columns: genderColumns },
                associated_diagnoses: { columns: associatedDiagnoses },
            };
            renderContentList(contentList, renderParams);
        })();
    }

    function runHierarchy() {
        let samples = getSelectedSamples();
        let sampleRequests = samples.map((s) => getSampleRequestFromSample(s));

        let request = {
            test_ids: compTests,
            z_value: compZValue,
            cluster_count: compClusterCount,
            samples: sampleRequests,
        };

        (async () => {
            const contentList = await performRequest("post", "hierarchy", request);

            let associatedDiagnoses = [{ accessor: "row_name", Header: "Заболевание" }];
            for (let i = 1; i <= compClusterCount; i++) {
                associatedDiagnoses.push({
                    accessor: `cluster${i}`,
                    Header: `Кластер ${i}`,
                    Cell: formatNonZeroOrEmpty,
                });
            }

            const renderParams = {
                test_stats: { columns: testAndAgeColumns },
                age_stats: { columns: testAndAgeColumns },
                gender_stats: { columns: genderColumns },
                associated_diagnoses: { columns: associatedDiagnoses },
            };
            renderContentList(contentList, renderParams);
        })();
    }

    const deleteBtn = (
        <button
            className="corner-bttn"
            onClick={() => showDeleteExperimentModal(experiment.index)}
        >
            <i className="fa fa-trash"></i>
        </button>
    );

    return (
        <Collapse
            className="instrument"
            size="small"
            activeKey={activated ? experiment.index : -1}
            onChange={() => {
                experiment.activated = !activated;
                setActivated(!activated);
            }}
        >
            <Panel header={name} key={experiment.index} extra={deleteBtn}>
                <div className="instrument-type">
                    <h6>Тип исследования:</h6>
                    <Select
                        listHeight={500}
                        className="select"
                        size="small"
                        showSearch
                        allowClear
                        placeholder="Please select"
                        onChange={(v) => {
                            setSelectedExperiment(v);
                            const exp = getExperimentByValue(v);
                            setComponentsToRender(exp.components);
                        }}
                        options={experimentData}
                    />
                    <button className="start-bttn" onClick={run}>
                        <i className="fa fa-play"></i> Запустить
                    </button>
                </div>

                <div className="instrument-panel">
                    <div className="instrument-result-container">{result}</div>

                    <div className="instrument-settings">
                        <div
                            className="instrument-settings-entry"
                            key={getUniqueKey()}
                            style={getRenderParams(Component.Sample)}
                        >
                            <div>Выборка для исследования:</div>
                            <Select
                                size="middle"
                                showSearch
                                allowClear
                                placeholder="Please select"
                                options={samplesData}
                                value={compSample}
                                onChange={setCompSample}
                            />
                        </div>

                        <div
                            className="instrument-settings-entry"
                            key={getUniqueKey()}
                            style={getRenderParams(Component.Samples)}
                        >
                            <div>Выборки для исследования:</div>
                            <Select
                                mode="multiple"
                                size="middle"
                                showSearch
                                allowClear
                                placeholder="Please select"
                                options={samplesData}
                                value={compSamples}
                                onChange={setCompSamples}
                            />
                        </div>

                        <div
                            className="instrument-settings-entry"
                            key={getUniqueKey()}
                            style={getRenderParams(Component.Tests)}
                        >
                            <div>Тесты для исследования:</div>
                            <Select
                                mode="multiple"
                                listHeight={500}
                                size="middle"
                                showSearch
                                allowClear
                                placeholder="Please select"
                                options={tests}
                                value={compTests}
                                onChange={setCompTests}
                            />
                        </div>

                        <div
                            className="instrument-settings-entry"
                            key={getUniqueKey()}
                            style={getRenderParams(Component.Test1)}
                        >
                            <div>Тест для исследования №1:</div>
                            <Select
                                listHeight={500}
                                size="middle"
                                showSearch
                                allowClear
                                options={tests}
                                value={compTest1}
                                onChange={setCompTest1}
                            />
                        </div>

                        <div
                            className="instrument-settings-entry"
                            key={getUniqueKey()}
                            style={getRenderParams(Component.Test2)}
                        >
                            <div>Тест для исследования №2:</div>
                            <Select
                                listHeight={500}
                                size="middle"
                                showSearch
                                allowClear
                                options={tests}
                                value={compTest2}
                                onChange={setCompTest2}
                            />
                        </div>

                        <div
                            className="instrument-settings-entry"
                            key={getUniqueKey()}
                            style={getRenderParams(Component.Bins)}
                        >
                            <div>Количество интервалов:</div>
                            <div>
                                <InputNumber
                                    size="middle"
                                    min={2}
                                    max={50}
                                    defaultValue={15}
                                    value={compBins}
                                    onChange={setCompBins}
                                />
                            </div>
                        </div>

                        <div
                            className="instrument-settings-entry"
                            key={getUniqueKey()}
                            style={getRenderParams(Component.ZValue)}
                        >
                            <div>Z-значение:</div>
                            <InputNumber
                                size="middle"
                                min={0.1}
                                max={10}
                                step="0.25"
                                defaultValue={3}
                                value={compZValue}
                                onChange={setCompZValue}
                            />
                        </div>

                        <div
                            className="instrument-settings-entry"
                            key={getUniqueKey()}
                            style={getRenderParams(Component.Kde)}
                        >
                            <div>Отображать кривую плотности:</div>
                            <Checkbox
                                checked={compUseKde}
                                onChange={(e) => setCompUseKde(e.target.checked)}
                            />
                        </div>

                        <div
                            className="instrument-settings-entry"
                            key={getUniqueKey()}
                            style={getRenderParams(Component.GroupBy)}
                        >
                            <div>Группировка:</div>
                            <Select
                                className="select"
                                size="middle"
                                placeholder="Please select"
                                options={groupByOptions}
                                value={compGroupBy}
                                onChange={setCompGroupBy}
                            />
                        </div>

                        <div
                            className="instrument-settings-entry"
                            key={getUniqueKey()}
                            style={getRenderParams(Component.CalcGenderStats)}
                        >
                            <div>Вычислять для пола:</div>
                            <Checkbox
                                checked={compCalcGenderStats}
                                onChange={(e) => setCompCalcGenderStats(e.target.checked)}
                            />
                        </div>

                        <div
                            className="instrument-settings-entry"
                            key={getUniqueKey()}
                            style={getRenderParams(Component.CalcAgeStats)}
                        >
                            <div>Вычислять для возраста:</div>
                            <Checkbox
                                checked={compCalcAgeStats}
                                onChange={(e) => setCompCalcAgeStats(e.target.checked)}
                            />
                        </div>

                        <div
                            className="instrument-settings-entry"
                            key={getUniqueKey()}
                            style={getRenderParams(Component.ClusterCount)}
                        >
                            <div>Количество кластеров:</div>
                            <div>
                                <InputNumber
                                    size="middle"
                                    min={2}
                                    max={10}
                                    defaultValue={3}
                                    value={compClusterCount}
                                    onChange={setCompClusterCount}
                                />
                            </div>
                        </div>

                        <div
                            className="instrument-settings-entry"
                            key={getUniqueKey()}
                            style={getRenderParams(Component.DistanceMetric)}
                        >
                            <div>Метрика дистанции:</div>
                            <Select
                                className="select"
                                size="middle"
                                placeholder="Please select"
                                options={distanceMetricOptions}
                                value={compDistanceMetric}
                                onChange={setCompDistanceMetric}
                            />
                        </div>

                        <div
                            className="instrument-settings-entry"
                            key={getUniqueKey()}
                            style={getRenderParams(Component.ExpectedMean)}
                        >
                            <div>Константа:</div>
                            <InputNumber
                                size="middle"
                                defaultValue={0}
                                value={compExpectedMean}
                                onChange={setCompExpectedMean}
                            />
                        </div>

                        <div
                            className="instrument-settings-entry"
                            key={getUniqueKey()}
                            style={getRenderParams(Component.Threshold)}
                        >
                            <div>Пороговое значение:</div>
                            <InputNumber
                                size="middle"
                                min={0.05}
                                max={1}
                                step="0.05"
                                defaultValue={0.05}
                                value={compThreshold}
                                onChange={setCompThreshold}
                            />
                        </div>
                    </div>
                </div>
            </Panel>
        </Collapse>
    );
}
