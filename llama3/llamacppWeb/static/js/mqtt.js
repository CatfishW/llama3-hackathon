/**
 * MQTT Communication Module
 * Handles MQTT connection and message publishing
 */

class MQTTConnector {
    constructor(config = {}) {
        this.config = {
            brokerURL: config.brokerURL || 'ws://47.89.252.2:9001',
            clientId: `web-client-${Math.random().toString(36).substr(2, 9)}`,
            username: config.username || null,
            password: config.password || null,
            ...config
        };

        this.client = null;
        this.connected = false;
        this.messageCallbacks = [];
        this.connectionCallbacks = [];
        this.disconnectionCallbacks = [];
    }

    /**
     * Connect to MQTT broker via WebSocket
     */
    connect() {
        return new Promise((resolve, reject) => {
            try {
                // Using paho-mqtt library
                const that = this;
                
                // Create client
                this.client = new Paho.MQTT.Client(
                    this.config.brokerURL.replace('ws://', '').split(':')[0],
                    9001,
                    this.config.clientId
                );

                // Set handlers
                this.client.onConnectionLost = (responseObject) => {
                    this._handleConnectionLost(responseObject);
                };

                this.client.onMessageArrived = (message) => {
                    this._handleMessageArrived(message);
                };

                // Connect options
                const connectOptions = {
                    useSSL: false,
                    cleanSession: true,
                    onSuccess: () => {
                        that.connected = true;
                        console.log('MQTT Connected');
                        that._notifyConnected();
                        resolve();
                    },
                    onFailure: (error) => {
                        console.error('MQTT Connection failed:', error);
                        reject(error);
                    }
                };

                if (this.config.username && this.config.password) {
                    connectOptions.userName = this.config.username;
                    connectOptions.password = this.config.password;
                }

                this.client.connect(connectOptions);

            } catch (error) {
                console.error('MQTT connection error:', error);
                reject(error);
            }
        });
    }

    /**
     * Disconnect from MQTT broker
     */
    disconnect() {
        if (this.client && this.client.isConnected()) {
            this.client.disconnect();
            this.connected = false;
            this._notifyDisconnected();
        }
    }

    /**
     * Subscribe to a topic
     */
    subscribe(topic, options = {}) {
        if (!this.client || !this.client.isConnected()) {
            console.error('MQTT not connected');
            return;
        }

        this.client.subscribe(topic, options);
        console.log(`Subscribed to topic: ${topic}`);
    }

    /**
     * Publish message to a topic
     */
    publish(topic, message, options = {}) {
        if (!this.client || !this.client.isConnected()) {
            console.error('MQTT not connected, cannot publish');
            return false;
        }

        try {
            const mqttMessage = new Paho.MQTT.Message(
                typeof message === 'string' ? message : JSON.stringify(message)
            );
            mqttMessage.destinationName = topic;
            mqttMessage.qos = options.qos || 0;
            mqttMessage.retained = options.retained || false;

            this.client.send(mqttMessage);
            console.log(`Published to ${topic}:`, message);
            return true;
        } catch (error) {
            console.error('Error publishing MQTT message:', error);
            return false;
        }
    }

    /**
     * Register callback for incoming messages
     */
    onMessage(callback) {
        this.messageCallbacks.push(callback);
    }

    /**
     * Register callback for connection
     */
    onConnected(callback) {
        this.connectionCallbacks.push(callback);
    }

    /**
     * Register callback for disconnection
     */
    onDisconnected(callback) {
        this.disconnectionCallbacks.push(callback);
    }

    /**
     * Handle connection lost
     */
    _handleConnectionLost(responseObject) {
        this.connected = false;
        if (responseObject.errorCode !== 0) {
            console.log(`MQTT Connection lost:`, responseObject.errorMessage);
        }
        this._notifyDisconnected();
    }

    /**
     * Handle message arrival
     */
    _handleMessageArrived(message) {
        try {
            let payload = message.payloadString;
            try {
                payload = JSON.parse(payload);
            } catch (e) {
                // Keep as string if not JSON
            }

            const msgObj = {
                topic: message.destinationName,
                message: payload,
                qos: message.qos,
                retained: message.retained
            };

            console.log('Message received:', msgObj);

            this.messageCallbacks.forEach(callback => {
                try {
                    callback(msgObj);
                } catch (error) {
                    console.error('Error in message callback:', error);
                }
            });
        } catch (error) {
            console.error('Error handling MQTT message:', error);
        }
    }

    /**
     * Notify connected
     */
    _notifyConnected() {
        this.connectionCallbacks.forEach(callback => {
            try {
                callback();
            } catch (error) {
                console.error('Error in connection callback:', error);
            }
        });
    }

    /**
     * Notify disconnected
     */
    _notifyDisconnected() {
        this.disconnectionCallbacks.forEach(callback => {
            try {
                callback();
            } catch (error) {
                console.error('Error in disconnection callback:', error);
            }
        });
    }

    /**
     * Check if connected
     */
    isConnected() {
        return this.connected && this.client && this.client.isConnected();
    }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MQTTConnector;
}
