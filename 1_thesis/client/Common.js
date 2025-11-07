import { v4 as uuidv4 } from "uuid";

export function showError(msg) {
    alert(msg);
    console.log(msg);
}

export function getUniqueKey() {
    return uuidv4();
}