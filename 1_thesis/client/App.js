import React from "react";

import { DatePicker, Layout, Typography, Modal, Input } from "antd";
import { performRequest } from "Api";
import { getUniqueKey } from "Common";
import Experiments from "Experiments";
import Samples from "Samples";

const { Paragraph, Title, Text, Link } = Typography;
const { RangePicker } = DatePicker;
const { Header, Footer, Sider, Content } = Layout;
const { confirm } = Modal;

function showError(error) {
    alert(error.message);
}

export default function App() {
    const dateFormat = "DD.MM.YYYY";
    const sendingFormat = "YYYY-MM-DD";

    const anyGenderString = "ANY";
    const maleGenderString = "м";
    const femaleGenderString = "ж";

    const [tests, setTests] = React.useState([]);
    const [diagnoses, setDiagnoses] = React.useState([]);

    const [samples, setSamples] = React.useState([]);
    const [experiments, setExperiments] = React.useState([]);

    const [sampleCount, setSampleCount] = React.useState(0);
    const [experimentCount, setExperimentCount] = React.useState(0);

    const [image, setImage] = React.useState();

    function getTests() {
        (async () => {
            const response = await performRequest("get", "tests");

            const oakValues = response.filter(
                (test) => test.analysis_name == "Общий анализ крови"
            );

            const bakValues = response.filter(
                (test) => test.analysis_name == "Биохимический анализ крови"
            );

            const converToSelectOptions = (array) =>
                array.map((test) => {
                    return {
                        label: `${test.name} [${test.count}]`,
                        value: test.id,
                        self: test,
                    };
                });

            const t = [
                {
                    label: "Общий анализ крови",
                    options: converToSelectOptions(oakValues),
                },
                {
                    label: "Биохимический анализ крови",
                    options: converToSelectOptions(bakValues),
                },
            ];

            setTests(t);
        })();
    }

    function getDiagnoses() {
        (async () => {
            const response = await performRequest("get", "diagnoses");

            const d = response.map((d) => {
                const group =
                    d.count != d.group_count && d.group_count != 0
                        ? `, сам диагноз ${d.group_count})`
                        : "";
                const code = d.code === "" ? "" : `${d.code} — `;
                return {
                    id: d.id,
                    pId: d.parent_id,
                    label: `${code}${d.name} (${d.count}${group})`,
                    value: d.id,
                };
            });

            setDiagnoses(d);
        })();
    }

    function getSearchedSamples() {
        // search should be based on index, diagnosis, and district
        // diagnosis search should be by name and/or mkb code but idk how to do that so :shrug:
        var input_ = document.getElementById("sample-search-input");
        if (input_ != null) {
            var filter_ = input_.value;
            var samples_ = document.getElementsByClassName("sample");
            for (var i = 0; i < samples_.length; i++) {
                if (filter_ == "" || samples_[i].innerText.split("\n")[0].toLowerCase().includes(filter_.toLowerCase())) {
                    samples_[i].style.display = "";
                } else {
                    samples_[i].style.display = "none";
                }
            }
        }
    }

    function addSample() {
        const newSample = {
            index: sampleCount + 1,
            key: getUniqueKey(),
            activated: true,
            name: `Выборка №${sampleCount + 1}`,
        };
        setSampleCount(sampleCount + 1);
        setSamples([...samples, newSample]);
    }

    function renameSample(index, newName) {
        if (newName !== "") {
            samples.find((item) => item.index === index).name = newName
            setSamples([...samples])
        }
    }

    function showRenameSampleModal(index) {
        let oldName = samples.find((item) => item.index === index).name
        confirm({
            title: "Изменение названия выборки",
            content:
            <div>
                <p>Введите новое название для выборки "{oldName}":</p>
                <Input id="rename-sample-input" size="small" defaultValue={oldName}/>
            </div>,
            okText: 'ОК',
            cancelText: 'Отмена',
            onOk() {renameSample(index, document.getElementById("rename-sample-input").value)},
        })
    }

    function deleteSample(index) {
        setSamples(samples.filter((item) => item.index !== index));
    }
    
    function showDeleteSampleModal(index) {
        confirm({
            title: "Удаление выборки",
            content: `Вы действительно хотите удалить выборку "${samples.find((item) => item.index === index).name}"?`,
            okText: 'ОК',
            cancelText: 'Отмена',
            onOk() {deleteSample(index)},
        })
    }

    function addExperiment() {
        const newExperiment = {
            index: experimentCount + 1,
            key: getUniqueKey(),
            activated: true,
        };
        setExperimentCount(experimentCount + 1);
        setExperiments([...experiments, newExperiment]);
    }

    function deleteExperiment(index) {
        setExperiments(experiments.filter((item) => item.index !== index));
    }

    function showDeleteExperimentModal(index) {
        confirm({
            title: "Удаление иследования",
            content: `Вы действительно хотите удалить исследование №${index}?`,
            onOk() {
                deleteExperiment(index)
            },
        })
    }

    React.useEffect(() => {
        getDiagnoses();
        getTests();

        addSample();
        addExperiment();
    }, []);

    return (
        <div>
            <div className="app-header">
                <div className="icon-and-title">
                    <img className="icon" src="icon.ico" />
                    <div className="title">StatMedLab</div>
                </div>

                <div className="links">
                    <a href="">Статьи</a>
                    <a href="">Исследования</a>
                    <a href="">Выход</a>
                </div>
            </div>

            <div className="app-sidebar">
                <input
                    className="sample-search"
                    type="text"
                    id="sample-search-input"
                    onChange={getSearchedSamples}
                    placeholder="Поиск выборки..."
                />

                <button className="create-bttn" onClick={addSample}>
                    + Создать новую выборку
                </button>

                <Samples
                    samples={samples}
                    diagnoses={diagnoses}
                    showRenameSampleModal={showRenameSampleModal}
                    showDeleteSampleModal={showDeleteSampleModal}
                />
            </div>

            
            <div className="app-main">
                <button className="create-bttn" onClick={addExperiment}>
                    + Создать новое исследование
                </button>

                <Experiments
                    experiments={experiments}
                    tests={tests}
                    samples={samples}
                    showDeleteExperimentModal={showDeleteExperimentModal}
                />
            </div>
        </div>
    );
}
