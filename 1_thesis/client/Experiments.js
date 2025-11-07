import { DatePicker, Layout, Typography } from "antd";
import Experiment from "Experiment";

const { Paragraph } = Typography;
const { RangePicker } = DatePicker;
const { Header, Footer, Sider, Content } = Layout;

function showError(error) {
    alert(error.message);
}

export default function Experiments({ experiments, tests, samples, showDeleteExperimentModal }) {
    return (
        <div className="instrument-container">
            {experiments.map((experiment) => (
                <Experiment
                    key={experiment.key}
                    experiment={experiment}
                    tests={tests}
                    samples={samples}
                    showDeleteExperimentModal={showDeleteExperimentModal}
                />
            ))}
        </div>
    );
}
