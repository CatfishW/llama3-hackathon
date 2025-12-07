#pragma once

#include <string>
#include <vector>
#include <map>
#include <optional>
#include <mutex>
#include <functional>
#include <nlohmann/json.hpp>
#include "config.hpp"

namespace prompt_portal {

struct ChatMessage {
    std::string role;     // "system", "user", or "assistant"
    std::string content;
};

/**
 * HTTP client for LLM inference using OpenAI-compatible API.
 * Supports llama.cpp server, vLLM, and other OpenAI-compatible endpoints.
 */
class LLMClient {
public:
    LLMClient();
    explicit LLMClient(const LlmConfig& config);
    
    /**
     * Generate response using OpenAI-compatible chat completion API.
     */
    std::string generate(
        const std::vector<ChatMessage>& messages,
        std::optional<double> temperature = std::nullopt,
        std::optional<double> top_p = std::nullopt,
        std::optional<int> max_tokens = std::nullopt,
        const std::string& model = "default"
    );
    
    /**
     * Generate streaming response (callback-based).
     */
    void generate_stream(
        const std::vector<ChatMessage>& messages,
        std::function<void(const std::string&)> on_chunk,
        std::optional<double> temperature = std::nullopt,
        std::optional<double> top_p = std::nullopt,
        std::optional<int> max_tokens = std::nullopt,
        const std::string& model = "default"
    );
    
    /**
     * Test connection to LLM server.
     */
    bool test_connection();
    
    // Getters
    std::string server_url() const { return server_url_; }
    double default_temperature() const { return default_temperature_; }
    int default_max_tokens() const { return default_max_tokens_; }
    bool is_available() const { return available_; }

private:
    std::string server_url_;
    int timeout_;
    double default_temperature_;
    double default_top_p_;
    int default_max_tokens_;
    bool skip_thinking_;
    bool available_ = false;
    
    std::string make_request(const std::string& endpoint, const nlohmann::json& body);
    void make_streaming_request(
        const std::string& endpoint, 
        const nlohmann::json& body,
        std::function<void(const std::string&)> on_chunk
    );
};

/**
 * Session manager for conversation history.
 */
class SessionManager {
public:
    explicit SessionManager(LLMClient& client, int max_history_messages = 20);
    
    /**
     * Process a user message and generate a response.
     */
    std::string process_message(
        const std::string& session_id,
        const std::string& system_prompt,
        const std::string& user_message,
        std::optional<double> temperature = std::nullopt,
        std::optional<double> top_p = std::nullopt,
        std::optional<int> max_tokens = std::nullopt
    );
    
    /**
     * Process message with streaming response.
     */
    void process_message_stream(
        const std::string& session_id,
        const std::string& system_prompt,
        const std::string& user_message,
        std::function<void(const std::string&)> on_chunk,
        std::optional<double> temperature = std::nullopt,
        std::optional<double> top_p = std::nullopt,
        std::optional<int> max_tokens = std::nullopt
    );
    
    /**
     * Get conversation history for a session.
     */
    std::optional<std::vector<ChatMessage>> get_session_history(const std::string& session_id);
    
    /**
     * Clear a session's history.
     */
    void clear_session(const std::string& session_id);

private:
    struct Session {
        std::vector<ChatMessage> dialog;
        int64_t created_at;
        int64_t last_access;
        int message_count = 0;
    };
    
    LLMClient& client_;
    int max_history_messages_;
    std::map<std::string, Session> sessions_;
    std::mutex sessions_mutex_;
    
    Session& get_or_create_session(const std::string& session_id, const std::string& system_prompt);
    void trim_history(Session& session);
};

// Global instances
LLMClient& get_llm_client();
SessionManager& get_session_manager();
void init_llm_service(const LlmConfig& config);

} // namespace prompt_portal

