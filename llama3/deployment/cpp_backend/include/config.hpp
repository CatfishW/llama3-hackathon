#pragma once

#include <string>
#include <vector>
#include <optional>

namespace openai_proxy {

/**
 * Server configuration loaded from environment variables or .env file.
 */
struct Config {
    // Upstream llama.cpp server URL
    std::string llama_base_url = "http://127.0.0.1:8080";
    
    // Default model name
    std::string default_model = "qwen3-30b-a3b-instruct";
    
    // API keys for authentication (empty = no auth required)
    std::vector<std::string> api_keys;
    
    // Request timeout in seconds
    int request_timeout = 300;
    
    // Maximum context characters (for truncation)
    int max_context_chars = 24000;
    
    // Server binding
    std::string host = "0.0.0.0";
    int port = 8000;
    
    // CORS settings
    bool enable_cors = true;
    std::string cors_origin = "*";
    
    // Logging
    bool verbose = false;
    
    // Load config from environment
    static Config from_env();
    
    // Load .env file
    static void load_dotenv(const std::string& path = ".env");
    
    // Check if authentication is required
    bool requires_auth() const { return !api_keys.empty(); }
};

// Global config accessor
Config& get_config();
void set_config(const Config& cfg);

} // namespace openai_proxy

