import { useEffect, useState } from "react";

import { Select, Typography } from "antd";
import axios from "axios";

var url = "http://127.0.0.1:5000/generate";

function toDict(array) {
    return array.map((x) => ({ label: x, value: x }));
}

async function getSuggestions(selectedItems) {
    var responde = await axios.post(url, { data: selectedItems }).catch(console.error);

    var result = responde.data.result;
    var suggestions = result;
    return suggestions;
}

export default SelectWithSuggestion();
{
    const [itemsToShow, setItemsToShow] = useState([]);
    const [selectedItems, setSelectedItems] = useState([]);

    async function setSuggestionItems(selectedItems) {
        var suggestions = await getSuggestions(selectedItems);
        setItemsToShow(toDict(suggestions));
    }

    async function itemSelected(newSelectedItems) {
        setSelectedItems(newSelectedItems);
        await setSuggestionItems(newSelectedItems);
    }

    useEffect(() => {
        setSuggestionItems([]).catch(console.error);
    }, []);

    return (
        <div>
            <Typography>Выбраны: {selectedItems.toString()}</Typography>
            <Typography>
                Подсказка: {itemsToShow.map((x) => x.value).toString()}
            </Typography>
            <Select
                mode="multiple"
                style={{ width: 300 }}
                options={itemsToShow}
                onChange={itemSelected}
            />
        </div>
    );
}
