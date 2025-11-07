import { DatePicker, Layout, Typography } from "antd";
import Sample from "Sample";

const { Paragraph } = Typography;
const { RangePicker } = DatePicker;
const { Header, Footer, Sider, Content } = Layout;

function showError(error) {
    alert(error.message);
}

export default function Samples({ samples, diagnoses, showRenameSampleModal, showDeleteSampleModal }) {
    return (
        <div className="sample-container">
            {samples.map((sample) => (
                <Sample
                    key={sample.key}
                    sample={sample}
                    diagnoses={diagnoses}
                    showRenameSampleModal={showRenameSampleModal}
                    showDeleteSampleModal={showDeleteSampleModal}
                />
            ))}
        </div>
    );
}
