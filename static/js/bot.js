import { appState, config } from './state.js';
import { makeApiRequest } from './api.js';
import {
    registeredBotsList, botNameInput, botIdInput, botTokenInput,
    webhookUrlInput, botManagementError, registerBotButton, clearErrors
} from './ui.js';

export async function loadBots() {
    if (!appState.activeBackend) return;
    registeredBotsList.innerHTML = '<tr><td colspan="2">Loading...</td></tr>';
    try {
        const bots = await makeApiRequest(`/api/${appState.activeBackend}/bots`, { method: 'GET' }, config.timeouts.loadChats);
        registeredBotsList.innerHTML = '';
        if (bots.length > 0) {
            bots.forEach(bot => {
                const row = registeredBotsList.insertRow();
                const nameCell = row.insertCell(0);
                const actionCell = row.insertCell(1);
                nameCell.textContent = bot.name;
                
                const deleteButton = document.createElement('button');
                deleteButton.textContent = '🗑️'; // Use a trash can emoji for a smaller button
                deleteButton.classList.add('delete-bot-button');
                deleteButton.title = `Delete ${bot.name}`;
                deleteButton.onclick = () => handleDeleteBot(bot.name);
                actionCell.appendChild(deleteButton);
            });
        } else {
            registeredBotsList.innerHTML = '<tr><td colspan="2">No bots registered for this service.</td></tr>';
        }
    } catch (error) {
        registeredBotsList.innerHTML = `<tr><td colspan="2" class="error-message">Error loading bots: ${error.message}</td></tr>`;
    }
}

export async function handleRegisterBot() {
    clearErrors();
    const name = botNameInput.value.trim();
    const bot_id = botIdInput.value.trim();
    const token = botTokenInput.value.trim();
    const webhook_url = webhookUrlInput.value.trim();

    if (appState.activeBackend === 'webex' && (!name || !token || !bot_id)) {
        botManagementError.textContent = 'Bot Name, Bot ID, and Token are required for Webex bots.';
        return;
    }
    
    if (appState.activeBackend === 'telegram' && (!name || !token)) {
        botManagementError.textContent = 'Bot Name and Token are required for Telegram bots.';
        return;
    }

    try {
        const payload = { name, token, bot_id: bot_id || 'telegram_bot' }; // Provide a dummy bot_id for telegram
        if (webhook_url) {
            payload.webhook_url = webhook_url;
        }
        await makeApiRequest(`/api/${appState.activeBackend}/bots`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        }, config.timeouts.login, registerBotButton);
        
        botNameInput.value = '';
        botIdInput.value = '';
        botTokenInput.value = '';
        webhookUrlInput.value = '';
        loadBots();
    } catch (error) {
        botManagementError.textContent = error.message || 'Failed to register bot.';
    }
}

export async function handleDeleteBot(botName) {
    if (!confirm(`Are you sure you want to delete the bot "${botName}"?`)) {
        return;
    }
    try {
        await makeApiRequest(`/api/${appState.activeBackend}/bots/${botName}`, { method: 'DELETE' }, config.timeouts.login);
        loadBots();
    } catch (error) {
        botManagementError.textContent = error.message || 'Failed to delete bot.';
    }
}