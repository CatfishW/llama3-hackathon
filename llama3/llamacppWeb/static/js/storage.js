/**
 * Local Storage Management Module
 * Handles chat history and settings persistence
 */

class StorageManager {
    constructor(storagePrefix = 'llamachat_') {
        this.prefix = storagePrefix;
        this.initializeStorage();
    }

    /**
     * Initialize storage with defaults if not exists
     */
    initializeStorage() {
        if (!this.get('settings')) {
            this.setSettings({
                theme: 'dark',
                autoSave: true,
                showTimestamps: true,
                temperature: 0.6,
                topP: 0.9,
                maxTokens: 512
            });
        }

        if (!this.get('chats')) {
            this.set('chats', {});
        }

        if (!this.get('sessions')) {
            this.set('sessions', {});
        }
    }

    /**
     * Get value from localStorage
     */
    get(key) {
        try {
            const value = localStorage.getItem(this.prefix + key);
            return value ? JSON.parse(value) : null;
        } catch (error) {
            console.error(`Error retrieving ${key} from storage:`, error);
            return null;
        }
    }

    /**
     * Set value in localStorage
     */
    set(key, value) {
        try {
            localStorage.setItem(this.prefix + key, JSON.stringify(value));
            return true;
        } catch (error) {
            console.error(`Error saving ${key} to storage:`, error);
            return false;
        }
    }

    /**
     * Remove value from localStorage
     */
    remove(key) {
        try {
            localStorage.removeItem(this.prefix + key);
            return true;
        } catch (error) {
            console.error(`Error removing ${key} from storage:`, error);
            return false;
        }
    }

    /**
     * Clear all data from localStorage
     */
    clear() {
        try {
            const keys = Object.keys(localStorage);
            keys.forEach(key => {
                if (key.startsWith(this.prefix)) {
                    localStorage.removeItem(key);
                }
            });
            this.initializeStorage();
            return true;
        } catch (error) {
            console.error('Error clearing storage:', error);
            return false;
        }
    }

    // ========== Settings Management ==========

    /**
     * Get all settings
     */
    getSettings() {
        return this.get('settings') || {};
    }

    /**
     * Update settings
     */
    setSettings(settings) {
        const current = this.getSettings();
        return this.set('settings', { ...current, ...settings });
    }

    /**
     * Get specific setting
     */
    getSetting(key) {
        const settings = this.getSettings();
        return settings[key];
    }

    /**
     * Set specific setting
     */
    setSetting(key, value) {
        const settings = this.getSettings();
        settings[key] = value;
        return this.set('settings', settings);
    }

    /**
     * Reset settings to defaults
     */
    resetSettings() {
        return this.setSettings({
            theme: 'dark',
            autoSave: true,
            showTimestamps: true,
            temperature: 0.6,
            topP: 0.9,
            maxTokens: 512
        });
    }

    // ========== Chat Management ==========

    /**
     * Create new chat
     */
    createChat(title = 'New Chat', project = 'general') {
        const chats = this.get('chats') || {};
        const chatId = `chat_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        
        chats[chatId] = {
            id: chatId,
            title: title,
            project: project,
            messages: [],
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            pinned: false
        };

        this.set('chats', chats);
        return chats[chatId];
    }

    /**
     * Get all chats
     */
    getAllChats() {
        const chats = this.get('chats') || {};
        return Object.values(chats).sort((a, b) => 
            new Date(b.updatedAt) - new Date(a.updatedAt)
        );
    }

    /**
     * Get chat by ID
     */
    getChat(chatId) {
        const chats = this.get('chats') || {};
        return chats[chatId];
    }

    /**
     * Update chat
     */
    updateChat(chatId, updates) {
        const chats = this.get('chats') || {};
        if (chats[chatId]) {
            chats[chatId] = {
                ...chats[chatId],
                ...updates,
                updatedAt: new Date().toISOString()
            };
            this.set('chats', chats);
            return chats[chatId];
        }
        return null;
    }

    /**
     * Add message to chat
     */
    addMessage(chatId, role, content, metadata = {}) {
        const chats = this.get('chats') || {};
        if (!chats[chatId]) return null;

        const message = {
            id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            role: role, // 'user' or 'assistant'
            content: content,
            timestamp: new Date().toISOString(),
            ...metadata
        };

        chats[chatId].messages.push(message);
        chats[chatId].updatedAt = new Date().toISOString();
        this.set('chats', chats);
        return message;
    }

    /**
     * Get messages from chat
     */
    getMessages(chatId) {
        const chats = this.get('chats') || {};
        return chats[chatId]?.messages || [];
    }

    /**
     * Update chat title
     */
    updateChatTitle(chatId, title) {
        return this.updateChat(chatId, { title });
    }

    /**
     * Delete chat
     */
    deleteChat(chatId) {
        const chats = this.get('chats') || {};
        delete chats[chatId];
        this.set('chats', chats);
        return true;
    }

    /**
     * Pin/unpin chat
     */
    togglePinChat(chatId) {
        const chats = this.get('chats') || {};
        if (chats[chatId]) {
            chats[chatId].pinned = !chats[chatId].pinned;
            this.set('chats', chats);
            return chats[chatId].pinned;
        }
        return null;
    }

    /**
     * Clear chat messages
     */
    clearChatMessages(chatId) {
        const chats = this.get('chats') || {};
        if (chats[chatId]) {
            chats[chatId].messages = [];
            chats[chatId].updatedAt = new Date().toISOString();
            this.set('chats', chats);
            return true;
        }
        return false;
    }

    /**
     * Export chat as JSON
     */
    exportChat(chatId) {
        const chat = this.getChat(chatId);
        if (!chat) return null;

        return {
            ...chat,
            exportedAt: new Date().toISOString()
        };
    }

    /**
     * Export all chats as JSON
     */
    exportAllChats() {
        const chats = this.getAllChats();
        return {
            chats: chats,
            exportedAt: new Date().toISOString(),
            version: '1.0'
        };
    }

    /**
     * Import chats from JSON
     */
    importChats(data) {
        try {
            if (!data.chats || !Array.isArray(data.chats)) {
                throw new Error('Invalid import data format');
            }

            const chats = this.get('chats') || {};
            data.chats.forEach(chat => {
                const newId = `chat_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
                chats[newId] = {
                    ...chat,
                    id: newId,
                    createdAt: new Date().toISOString(),
                    updatedAt: new Date().toISOString()
                };
            });

            this.set('chats', chats);
            return true;
        } catch (error) {
            console.error('Error importing chats:', error);
            return false;
        }
    }

    // ========== Session Management ==========

    /**
     * Save session ID for a chat
     */
    saveSession(chatId, sessionId) {
        const sessions = this.get('sessions') || {};
        sessions[chatId] = {
            sessionId: sessionId,
            createdAt: new Date().toISOString()
        };
        this.set('sessions', sessions);
    }

    /**
     * Get session ID for a chat
     */
    getSession(chatId) {
        const sessions = this.get('sessions') || {};
        return sessions[chatId]?.sessionId;
    }

    /**
     * Generate new session ID
     */
    generateSessionId() {
        return `sess_${Date.now()}_${Math.random().toString(36).substr(2, 16)}`;
    }

    /**
     * Clear session
     */
    clearSession(chatId) {
        const sessions = this.get('sessions') || {};
        delete sessions[chatId];
        this.set('sessions', sessions);
    }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = StorageManager;
}
