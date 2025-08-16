// --- Global State & Configuration ---
export const appState = {
    isProcessing: {
        login: false,
        chats: false,
        analysis: false,
        session: false,
    },
    chatRequestController: null,
    chatLoadController: null,
    activeBackend: null, // 'telegram' or 'webex'
    sessionTokens: { telegram: null, webex: null, reddit: null }, // The single source of truth for auth
    activeSection: 'login',
    modelsLoaded: false,
    chatListStatus: { telegram: 'unloaded', webex: 'unloaded', reddit: 'unloaded' },
    conversation: [], // Holds the current chat history {role, content}
    postChoicesInstance: null,
};

export const CACHE_CHATS_KEY = 'chat_analyzer_cache_chats_enabled';

// Namespaced Local Storage Keys
export const ACTIVE_BACKEND_KEY = 'chat_analyzer_active_backend';
export const getSessionTokenKey = (backend) => `chat_analyzer_${backend}_session_token`;
export const IMAGE_PROCESSING_ENABLED_KEY = 'chat_analyzer_image_processing_enabled';
export const MAX_IMAGE_SIZE_KEY = 'chat_analyzer_max_image_size';

export const config = {
    timeouts: {
        verify: 180000, summary: 180000, loadChats: 30000,
        logout: 15000, login: 30000, loadModels: 20000,
    }
};
