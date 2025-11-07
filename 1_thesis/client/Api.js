import axios from "axios";
import { showError } from "Common";

const instance = axios.create({
    baseURL: process.env.REACT_APP_DOMAIN + "/api/",
});

export async function performRequest(method, url, request = null) {
    console.log('request', method, url, request);
    let response = null;
    try {
        response = await instance({ method: method, url: url, data: request });
    } catch (e) {
        showError(e);
    }

    return response.data;
}
