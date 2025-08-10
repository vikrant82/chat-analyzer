import { appState } from './state.js';
import { setLoadingState } from './ui.js';

export async function makeApiRequest(url, options, timeoutDuration, elementToLoad = null, loadingText = 'Processing...', operationType = 'login') {
    if (appState.isProcessing[operationType]) {
        throw new Error('Operation already in progress.');
    }
    appState.isProcessing[operationType] = true;
    if (elementToLoad) setLoadingState(elementToLoad, true, loadingText);

    const controller = new AbortController();
    if (operationType === 'chats') {
        appState.chatLoadController = controller;
    }
    const timeoutId = setTimeout(() => controller.abort(), timeoutDuration);

    const finalOptions = {
        ...options,
        headers: {
            ...(options.headers || {}),
        },
        signal: controller.signal,
    };

    const token = appState.sessionTokens[appState.activeBackend];
    if (token) {
        finalOptions.headers['Authorization'] = `Bearer ${token}`;
    }

    try {
        const response = await fetch(url, finalOptions);
        clearTimeout(timeoutId);
        if (!response.ok) {
            let errorDetail = `Request failed with status ${response.status}`;
            try {
                const errorData = await response.json();
                errorDetail = errorData.detail || JSON.stringify(errorData);
            } catch (e) {
                errorDetail = response.statusText || errorDetail;
            }
            throw new Error(`API Error (${response.status}): ${errorDetail}`);
        }
        if (response.status === 204) {
            return {};
        }
        // Try to parse JSON, as most API endpoints return it.
        try {
            return await response.json();
        } catch (e) {
            const contentType = response.headers.get("content-type");
            // If parsing fails but the server claimed it was JSON, it's a server error.
            if (contentType && contentType.includes("application/json")) {
                console.error("Failed to parse JSON response:", e);
                throw new Error("Received malformed JSON from server.");
            }
            // If it wasn't supposed to be JSON, return empty object to not break callers.
            return {};
        }
    } catch (error) {
        clearTimeout(timeoutId);
        if (error.name === 'AbortError') {
            throw new Error(`Request timed out.`);
        }
        throw error;
    } finally {
        appState.isProcessing[operationType] = false;
        if (elementToLoad) setLoadingState(elementToLoad, false);
    }
}