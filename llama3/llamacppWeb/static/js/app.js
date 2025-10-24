/**
 * Main Application Module
 * Orchestrates UI, MQTT communication, and data management
 */

class LlamaChatApp {
    constructor() {
        this.storage = new StorageManager();
        this.mqtt = null;
        this.currentChatId = null;
        this.currentProject = 'general';
        this.waitingForResponse = false;
        this.sessionId = null;
        this.messageQueue = [];

        this.initializeUI();
        this.setupEventListeners();
        this.applySettings();
        this.initializeMQTT();
        this.loadChatHistory();
    }

    // ========== INITIALIZATION ==========

    initializeUI() {
        this.elements = {
            // Chat area
            messagesContainer: document.getElementById('messagesContainer'),
            messageInput: document.getElementById('messageInput'),
            sendBtn: document.getElementById('sendBtn'),
            
            // Chat list
            chatList: document.getElementById('chatList'),
            newChatBtn: document.getElementById('newChatBtn'),
            
            // Header
            chatTitle: document.getElementById('chatTitle'),
            projectInfo: document.getElementById('projectInfo'),
            
            // Project selector
            projectSelect: document.getElementById('projectSelect'),
            
            // Input controls
            tokenCount: document.getElementById('tokenCount'),
            expandOptionsBtn: document.getElementById('expandOptionsBtn'),
            optionsPanel: document.getElementById('optionsPanel'),
            
            // Sliders
            temperatureSlider: document.getElementById('temperatureSlider'),
            temperatureValue: document.getElementById('temperatureValue'),
            topPSlider: document.getElementById('topPSlider'),
            topPValue: document.getElementById('topPValue'),
            maxTokensSlider: document.getElementById('maxTokensSlider'),
            maxTokensValue: document.getElementById('maxTokensValue'),
            
            // Checkboxes
            useSystemPromptCheckbox: document.getElementById('useSystemPromptCheckbox'),
            customSystemPrompt: document.getElementById('customSystemPrompt'),
            
            // Status
            statusIndicator: document.getElementById('statusIndicator'),
            statusText: document.getElementById('statusText'),
            
            // Buttons
            deleteBtn: document.getElementById('deleteBtn'),
            settingsBtn: document.getElementById('settingsBtn'),
            helpBtn: document.getElementById('helpBtn'),
            
            // Modals
            settingsModal: document.getElementById('settingsModal'),
            helpModal: document.getElementById('helpModal'),
            closeSettingsBtn: document.getElementById('closeSettingsBtn'),
            closeHelpBtn: document.getElementById('closeHelpBtn'),
            saveSettingsBtn: document.getElementById('saveSettingsBtn'),
            resetSettingsBtn: document.getElementById('resetSettingsBtn'),
            
            // Settings inputs
            autoSaveChats: document.getElementById('autoSaveChats'),
            showTimestamps: document.getElementById('showTimestamps'),
            themeSelect: document.getElementById('themeSelect'),
            
            // Toast
            toastContainer: document.getElementById('toastContainer')
        };

        this.updateStatusBar('disconnected', 'Disconnected');
    }

    setupEventListeners() {
        // Message sending
        this.elements.messageInput.addEventListener('keydown', (e) => this.handleMessageInput(e));
        this.elements.sendBtn.addEventListener('click', () => this.sendMessage());

        // Chat management
        this.elements.newChatBtn.addEventListener('click', () => this.createNewChat());
        this.elements.deleteBtn.addEventListener('click', () => this.deleteCurrentChat());

        // Project selection
        this.elements.projectSelect.addEventListener('change', (e) => this.selectProject(e.target.value));

        // Advanced options
        this.elements.expandOptionsBtn.addEventListener('click', () => this.toggleOptionsPanel());
        this.elements.temperatureSlider.addEventListener('input', (e) => {
            this.elements.temperatureValue.textContent = e.target.value;
            this.storage.setSetting('temperature', parseFloat(e.target.value));
        });
        this.elements.topPSlider.addEventListener('input', (e) => {
            this.elements.topPValue.textContent = e.target.value;
            this.storage.setSetting('topP', parseFloat(e.target.value));
        });
        this.elements.maxTokensSlider.addEventListener('input', (e) => {
            this.elements.maxTokensValue.textContent = e.target.value;
            this.storage.setSetting('maxTokens', parseInt(e.target.value));
        });

        // Settings modal
        this.elements.settingsBtn.addEventListener('click', () => this.showSettingsModal());
        this.elements.helpBtn.addEventListener('click', () => this.showHelpModal());
        this.elements.closeSettingsBtn.addEventListener('click', () => this.hideSettingsModal());
        this.elements.closeHelpBtn.addEventListener('click', () => this.hideHelpModal());
        this.elements.saveSettingsBtn.addEventListener('click', () => this.saveSettings());
        this.elements.resetSettingsBtn.addEventListener('click', () => this.resetSettings());

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboardShortcuts(e));

        // Click outside modals to close
        window.addEventListener('click', (e) => {
            if (e.target === this.elements.settingsModal) this.hideSettingsModal();
            if (e.target === this.elements.helpModal) this.hideHelpModal();
        });
    }

    applySettings() {
        const settings = this.storage.getSettings();
        
        // Apply theme
        if (settings.theme === 'light') {
            document.body.classList.add('light-theme');
        }

        // Update sliders
        this.elements.temperatureSlider.value = settings.temperature;
        this.elements.temperatureValue.textContent = settings.temperature;
        this.elements.topPSlider.value = settings.topP;
        this.elements.topPValue.textContent = settings.topP;
        this.elements.maxTokensSlider.value = settings.maxTokens;
        this.elements.maxTokensValue.textContent = settings.maxTokens;

        // Update checkboxes
        this.elements.autoSaveChats.checked = settings.autoSave;
        this.elements.showTimestamps.checked = settings.showTimestamps;
        this.elements.themeSelect.value = settings.theme;
    }

    // ========== MQTT INITIALIZATION ==========

    initializeMQTT() {
        this.mqtt = new MQTTConnector({
            brokerURL: `ws://${this.storage.getSetting('mqttServer') || '47.89.252.2'}:9001`
        });

        this.mqtt.onConnected(() => {
            this.updateStatusBar('connected', 'Connected');
            this.showToast('Connected to MQTT broker', 'success');
        });

        this.mqtt.onDisconnected(() => {
            this.updateStatusBar('disconnected', 'Disconnected');
            this.showToast('Disconnected from MQTT broker', 'error');
            // Attempt reconnection
            setTimeout(() => this.reconnectMQTT(), 3000);
        });

        this.mqtt.onMessage((msg) => {
            this.handleMQTTMessage(msg);
        });

        this.connectMQTT();
    }

    connectMQTT() {
        this.updateStatusBar('loading', 'Connecting...');
        this.mqtt.connect()
            .catch(error => {
                console.error('Failed to connect to MQTT:', error);
                this.showToast('Failed to connect to MQTT broker', 'error');
                setTimeout(() => this.reconnectMQTT(), 5000);
            });
    }

    reconnectMQTT() {
        if (!this.mqtt.isConnected()) {
            this.connectMQTT();
        }
    }

    // ========== CHAT MANAGEMENT ==========

    createNewChat() {
        const chat = this.storage.createChat(
            `Chat - ${new Date().toLocaleString()}`,
            this.currentProject
        );
        this.sessionId = this.storage.generateSessionId();
        this.storage.saveSession(chat.id, this.sessionId);
        this.loadChat(chat.id);
        this.showToast('New chat created', 'success');
    }

    loadChat(chatId) {
        this.currentChatId = chatId;
        const chat = this.storage.getChat(chatId);
        
        if (!chat) return;

        this.currentProject = chat.project;
        this.elements.projectSelect.value = chat.project;
        this.elements.chatTitle.textContent = chat.title;
        this.elements.projectInfo.textContent = `Project: ${chat.project}`;
        this.sessionId = this.storage.getSession(chatId);

        // Clear messages and reload
        this.elements.messagesContainer.innerHTML = '';
        const messages = this.storage.getMessages(chatId);
        
        if (messages.length === 0) {
            this.showWelcomeMessage();
        } else {
            messages.forEach(msg => this.displayMessage(msg.role, msg.content, msg.timestamp));
        }

        this.updateChatList();
        this.scrollToBottom();
    }

    deleteCurrentChat() {
        if (!this.currentChatId || !confirm('Are you sure you want to delete this chat?')) {
            return;
        }

        this.storage.deleteChat(this.currentChatId);
        this.currentChatId = null;
        this.createNewChat();
        this.showToast('Chat deleted', 'success');
    }

    selectProject(project) {
        this.currentProject = project;
        this.elements.projectInfo.textContent = `Project: ${project}`;
        
        if (this.currentChatId) {
            this.storage.updateChat(this.currentChatId, { project });
        }
    }

    // ========== MESSAGE HANDLING ==========

    handleMessageInput(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            this.sendMessage();
        }
    }

    sendMessage() {
        const message = this.elements.messageInput.value.trim();
        
        if (!message) return;
        if (this.waitingForResponse) {
            this.showToast('Waiting for response...', 'info');
            return;
        }
        if (!this.mqtt.isConnected()) {
            this.showToast('Not connected to MQTT broker', 'error');
            return;
        }

        // Ensure we have a chat and session
        if (!this.currentChatId) {
            this.createNewChat();
        }
        if (!this.sessionId) {
            this.sessionId = this.storage.generateSessionId();
            this.storage.saveSession(this.currentChatId, this.sessionId);
        }

        // Store message
        this.storage.addMessage(this.currentChatId, 'user', message);
        this.displayMessage('user', message);

        // Clear input
        this.elements.messageInput.value = '';
        this.elements.messageInput.style.height = 'auto';

        // Remove welcome message if present
        const welcomeMsg = this.elements.messagesContainer.querySelector('.welcome-message');
        if (welcomeMsg) {
            welcomeMsg.remove();
        }

        // Publish to MQTT
        this.publishMessage(message);
    }

    publishMessage(message) {
        this.waitingForResponse = true;
        this.elements.sendBtn.disabled = true;

        const responseTopic = `${this.currentProject}/assistant_response/${this.sessionId}`;
        const userTopic = `${this.currentProject}/user_input`;

        // Subscribe to response topic
        this.mqtt.subscribe(responseTopic);

        // Prepare message payload
        const payload = {
            sessionId: this.sessionId,
            message: message,
            project: this.currentProject,
            temperature: parseFloat(this.elements.temperatureSlider.value),
            topP: parseFloat(this.elements.topPSlider.value),
            maxTokens: parseInt(this.elements.maxTokensSlider.value),
            replyTopic: responseTopic
        };

        if (this.elements.useSystemPromptCheckbox.checked && this.elements.customSystemPrompt.value) {
            payload.systemPrompt = this.elements.customSystemPrompt.value;
        }

        // Show loading indicator
        this.showLoadingIndicator();

        // Publish
        this.mqtt.publish(userTopic, payload);

        // Set timeout for response
        this.responseTimeout = setTimeout(() => {
            if (this.waitingForResponse) {
                this.waitingForResponse = false;
                this.elements.sendBtn.disabled = false;
                this.removeLoadingIndicator();
                this.showToast('Response timeout - server may be busy', 'error');
            }
        }, 60000); // 60 second timeout
    }

    handleMQTTMessage(msg) {
        console.log('MQTT Message:', msg);

        // Check if this is a response we're waiting for
        if (msg.topic.includes('assistant_response') && msg.topic.includes(this.sessionId)) {
            this.waitingForResponse = false;
            this.elements.sendBtn.disabled = false;

            if (this.responseTimeout) {
                clearTimeout(this.responseTimeout);
            }

            this.removeLoadingIndicator();

            // Extract message content
            let response = msg.message;
            if (typeof response === 'object') {
                response = JSON.stringify(response, null, 2);
            }

            // Store and display
            this.storage.addMessage(this.currentChatId, 'assistant', response);
            this.displayMessage('assistant', response);
            this.scrollToBottom();
        }
    }

    // ========== UI RENDERING ==========

    displayMessage(role, content, timestamp = null) {
        const messageEl = document.createElement('div');
        messageEl.className = `message ${role}`;

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = role === 'user' ? '👤' : '🦙';

        const contentEl = document.createElement('div');
        contentEl.className = 'message-content';

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        bubble.textContent = content;

        contentEl.appendChild(bubble);

        if (this.storage.getSetting('showTimestamps') && timestamp) {
            const time = document.createElement('div');
            time.className = 'message-time';
            time.textContent = new Date(timestamp).toLocaleTimeString();
            contentEl.appendChild(time);
        }

        messageEl.appendChild(avatar);
        messageEl.appendChild(contentEl);

        this.elements.messagesContainer.appendChild(messageEl);
        this.scrollToBottom();
    }

    showWelcomeMessage() {
        const welcomeMsg = document.createElement('div');
        welcomeMsg.className = 'welcome-message';
        welcomeMsg.innerHTML = `
            <div class="welcome-content">
                <h2>👋 Welcome to Llama Chat</h2>
                <p>Start a conversation with the AI assistant powered by Llama.cpp</p>
                <div class="feature-list">
                    <div class="feature">📚 Multi-project support</div>
                    <div class="feature">💾 Chat history saved locally</div>
                    <div class="feature">⚡ Real-time responses</div>
                    <div class="feature">🔐 MQTT-based communication</div>
                </div>
            </div>
        `;
        this.elements.messagesContainer.appendChild(welcomeMsg);
    }

    showLoadingIndicator() {
        const loadingEl = document.createElement('div');
        loadingEl.className = 'message assistant';
        loadingEl.id = 'loading-indicator';
        loadingEl.innerHTML = `
            <div class="message-avatar">🦙</div>
            <div class="message-content">
                <div class="message-loading">
                    <div class="loading-dot"></div>
                    <div class="loading-dot"></div>
                    <div class="loading-dot"></div>
                </div>
            </div>
        `;
        this.elements.messagesContainer.appendChild(loadingEl);
        this.scrollToBottom();
    }

    removeLoadingIndicator() {
        const loadingEl = document.getElementById('loading-indicator');
        if (loadingEl) {
            loadingEl.remove();
        }
    }

    scrollToBottom() {
        this.elements.messagesContainer.scrollTop = this.elements.messagesContainer.scrollHeight;
    }

    loadChatHistory() {
        this.updateChatList();
        const chats = this.storage.getAllChats();
        
        if (chats.length === 0) {
            this.createNewChat();
        } else {
            this.loadChat(chats[0].id);
        }
    }

    updateChatList() {
        const chats = this.storage.getAllChats();
        this.elements.chatList.innerHTML = '';

        chats.forEach(chat => {
            const chatItem = document.createElement('div');
            chatItem.className = `chat-item ${chat.id === this.currentChatId ? 'active' : ''}`;
            chatItem.textContent = chat.title.substring(0, 40);
            chatItem.addEventListener('click', () => this.loadChat(chat.id));

            // Add delete on right click
            chatItem.addEventListener('contextmenu', (e) => {
                e.preventDefault();
                if (confirm('Delete this chat?')) {
                    this.storage.deleteChat(chat.id);
                    this.updateChatList();
                    if (this.currentChatId === chat.id) {
                        this.createNewChat();
                    }
                }
            });

            this.elements.chatList.appendChild(chatItem);
        });
    }

    // ========== SETTINGS & OPTIONS ==========

    toggleOptionsPanel() {
        const panel = this.elements.optionsPanel;
        const isVisible = panel.style.display !== 'none';
        panel.style.display = isVisible ? 'none' : 'block';
        
        const btn = this.elements.expandOptionsBtn;
        btn.textContent = isVisible ? '▼ Advanced Options' : '▲ Advanced Options';
    }

    showSettingsModal() {
        this.elements.settingsModal.style.display = 'flex';
    }

    hideSettingsModal() {
        this.elements.settingsModal.style.display = 'none';
    }

    showHelpModal() {
        this.elements.helpModal.style.display = 'flex';
    }

    hideHelpModal() {
        this.elements.helpModal.style.display = 'none';
    }

    saveSettings() {
        const settings = {
            autoSave: this.elements.autoSaveChats.checked,
            showTimestamps: this.elements.showTimestamps.checked,
            theme: this.elements.themeSelect.value
        };

        this.storage.setSettings(settings);

        // Apply theme
        if (settings.theme === 'light') {
            document.body.classList.add('light-theme');
        } else {
            document.body.classList.remove('light-theme');
        }

        this.hideSettingsModal();
        this.showToast('Settings saved successfully', 'success');
    }

    resetSettings() {
        if (confirm('Are you sure you want to reset all settings to defaults?')) {
            this.storage.resetSettings();
            this.applySettings();
            this.showToast('Settings reset to defaults', 'success');
        }
    }

    // ========== UTILITIES ==========

    updateStatusBar(status, text) {
        this.elements.statusIndicator.className = `status-indicator ${status}`;
        this.elements.statusText.textContent = text;
    }

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icon = type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ';
        toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;

        this.elements.toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideInRight 0.3s ease-out reverse';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    handleKeyboardShortcuts(e) {
        if (e.ctrlKey || e.metaKey) {
            if (e.key === 'k') {
                e.preventDefault();
                this.createNewChat();
            } else if (e.key === 'l') {
                e.preventDefault();
                if (this.currentChatId) {
                    this.storage.clearChatMessages(this.currentChatId);
                    this.loadChat(this.currentChatId);
                }
            }
        }
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new LlamaChatApp();
    console.log('Llama Chat App initialized');
});
