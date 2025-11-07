import React from "react";

import {
    Checkbox,
    Collapse,
    DatePicker,
    Layout,
    Select,
    InputNumber,
    Slider,
    Tag,
    TreeSelect,
    Typography
} from "antd";
import dayjs from "dayjs";

const { Title } = Typography;
const { Paragraph } = Typography;
const { RangePicker } = DatePicker;
const { Header, Footer, Sider, Content } = Layout;
const { Panel } = Collapse;

function getChildrenOfElem(elem, diagnoses) {
    let result = diagnoses.filter((value) => value.pId === elem).map((value) => value.id);

    if (result.length === 0) {
        return null;
    } else {
        return getChildrenOfElems(result, diagnoses);
    }
}

function getChildrenOfElems(elems, diagnoses) {
    let result = elems.slice();
    for (const elem of elems) {
        const children = getChildrenOfElem(elem, diagnoses);
        if (children !== null) {
            result = result.concat(children);
        }
    }
    return result;
}

const tagRender = (props) => {
    if (props.label === "-1") return <div></div>;

    const code = props.label.split("—")[0].trim();
    const tag = (
        <Tag closable onClose={props.onClose}>
            {code}
        </Tag>
    );
    return tag;
};

export default function Sample({ sample, diagnoses, showRenameSampleModal, showDeleteSampleModal }) {
    const dateFormat = "DD.MM.YYYY";
    const startDate = dayjs("10.10.2018", dateFormat);
    const endDate = dayjs("13.06.2019", dateFormat);
    
    const initAgeMin = 0;
    const initAgeMax = 100;

    const [activated, setActivated] = React.useState(sample.activated);
    const [[minAge, maxAge], ageLimits] = React.useState([initAgeMin, initAgeMax]);

    const setAgeInterval = (val) => {ageLimits(val); sample.ageInterval = val};
    const setGenderMale = (val) => (sample.genderMale = val);
    const setGenderFemale = (val) => (sample.genderFemale = val);
    const setDiagnoses = (val) => (sample.diagnoses = val);
    const setDistrict = (val) => (sample.district = val);
    const setTimeInterval = (val) => (sample.timeInterval = val);

    React.useEffect(() => {
        setAgeInterval([initAgeMin, initAgeMax]);
        setGenderMale(true);
        setGenderFemale(true);
        setDiagnoses([]);
        setDistrict([]);
        setTimeInterval([startDate, endDate]);
    }, []);

    const cornerBttns = (
        <div>
            <button className="corner-bttn" onClick={() => showRenameSampleModal(sample.index)}>
                <i className="fa fa-pencil"></i>
            </button>
            <button className="corner-bttn" onClick={() => showDeleteSampleModal(sample.index)}>
                <i className="fa fa-trash"></i>
            </button>
        </div>
    );

    return (
        <Collapse
            className="sample"
            size="small"
            activeKey={activated ? sample.index : -1}
            onChange={() => {
                sample.activated = !activated;
                setActivated(!activated);
            }}
        >
            <Panel
                header={`${sample.name}`}
                key={sample.index}
                extra={cornerBttns}
            >
                <div className="filter">
                    Пол:
                    <div className="filter-settings">
                        <Checkbox
                            defaultChecked={true}
                            onChange={(e) => setGenderMale(e.target.checked)}
                        >
                            Мужской
                        </Checkbox>
                        <Checkbox
                            defaultChecked={true}
                            onChange={(e) => setGenderFemale(e.target.checked)}
                        >
                            Женский
                        </Checkbox>
                    </div>
                </div>

                <div className="filter">
                    Возраст:
                    <InputNumber
                        className="filter-settings"
                        style={{width: "30%"}}
                        size="small"
                        min={initAgeMin}
                        max={initAgeMax}
                        step={5}
                        value={minAge}
                        onChange={(value) => {setAgeInterval([value, sample.ageInterval[1]])}}
                    />
                    <Slider
                        id="testtest"
                        className="filter-settings"
                        onChange={setAgeInterval}
                        range
                        defaultValue={[initAgeMin, initAgeMax]}
                        value={[minAge, maxAge]}
                    ></Slider>
                    <InputNumber
                        className="filter-settings"
                        style={{width: "30%"}}
                        size="small"
                        min={initAgeMin}
                        max={initAgeMax}
                        step={5}
                        value={maxAge}
                        onChange={(value) => {setAgeInterval([sample.ageInterval[0], value])}}
                    />
                </div>

                <div className="filter">
                    Диагнозы:
                    <TreeSelect
                        // treeExpandedKeys={[-1]}
                        className="filter-settings"
                        dropdownStyle={{ minWidth: "1400px" }}
                        listHeight={400}
                        placeholder="Please select"
                        placement="bottomLeft"
                        showSearch
                        size="small"
                        tagRender={tagRender}
                        treeCheckable
                        treeData={diagnoses}
                        treeDataSimpleMode
                        showCheckedStrategy={TreeSelect.SHOW_PARENT}
                        onChange={(values) => {
                            if (values.length === 1 && values[0] === -1) {
                                setDiagnoses([]);
                            } else {
                                const children = getChildrenOfElems(
                                    values,
                                    diagnoses
                                ).sort();
                                const d = diagnoses.filter((v) =>
                                    children.includes(v.id)
                                );
                                setDiagnoses(children);
                            }
                        }}
                    />
                </div>

                <div className="filter">
                    Район:
                    <TreeSelect
                        className="filter-settings"
                        mode="multiple"
                        size="small"
                        showSearch
                        allowClear
                        placeholder="Please select"
                        treeCheckable
                        treeData={[
                            {id:0, value:-1, title:"Все доступные"},
                            {id:10, pId:0, value:1, title:"Кондинский"},
                            {id:20, pId:0, value:2, title:"Ишимский"},
                        ]}
                        treeDataSimpleMode
                        showCheckedStrategy={TreeSelect.SHOW_PARENT}
                        onChange={(values) => setDistrict(values)}
                    />
                </div>

                <div className="filter">
                    Дата сдачи анализа:
                    <RangePicker
                        className="filter-settings"
                        size="small"
                        onChange={(value) => setTimeInterval(value)}
                        defaultValue={[startDate, endDate]}
                        format={dateFormat}
                        allowClear={false}
                    />
                </div>
            </Panel>
        </Collapse>
    );
}
