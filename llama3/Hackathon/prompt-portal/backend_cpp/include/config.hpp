#pragma once

#include <string>
#include <vector>
#include <fstream>
#include <nlohmann/json.hpp>

namespace prompt_portal {

struct ServerConfig {
    std::string host = "0.0.0.0";
    int port = 8000;
    int threads = 4;
};

struct DatabaseConfig {
    std::string path = "./app.db";
};

struct AuthConfig {
    std::string secret_key = "change_me_in_production";
    std::string algorithm = "HS256";
    int token_expire_minutes = 60;
};

struct CorsConfig {
    std::vector<std::string> allowed_origins;
    bool allow_credentials = true;
    std::vector<std::string> allowed_methods;
    std::vector<std::string> allowed_headers;
};

struct LlmConfig {
    std::string server_url = "http://localhost:8080";
    int timeout = 300;
    double temperature = 0.6;
    double top_p = 0.9;
    int max_tokens = 4096;
};

struct Config {
    ServerConfig server;
    DatabaseConfig database;
    AuthConfig auth;
    CorsConfig cors;
    LlmConfig llm;

    static Config load(const std::string& path = "config.json") {
        Config config;
        
        std::ifstream file(path);
        if (!file.is_open()) {
            // Return default config if file doesn't exist
            config.cors.allowed_origins = {
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:3000",
                "http://127.0.0.1:3000"
            };
            config.cors.allowed_methods = {"GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"};
            config.cors.allowed_headers = {"*"};
            return config;
        }

        nlohmann::json j;
        file >> j;

        // Parse server config
        if (j.contains("server")) {
            auto& s = j["server"];
            if (s.contains("host")) config.server.host = s["host"];
            if (s.contains("port")) config.server.port = s["port"];
            if (s.contains("threads")) config.server.threads = s["threads"];
        }

        // Parse database config
        if (j.contains("database")) {
            auto& d = j["database"];
            if (d.contains("path")) config.database.path = d["path"];
        }

        // Parse auth config
        if (j.contains("auth")) {
            auto& a = j["auth"];
            if (a.contains("secret_key")) config.auth.secret_key = a["secret_key"];
            if (a.contains("algorithm")) config.auth.algorithm = a["algorithm"];
            if (a.contains("token_expire_minutes")) config.auth.token_expire_minutes = a["token_expire_minutes"];
        }

        // Parse CORS config
        if (j.contains("cors")) {
            auto& c = j["cors"];
            if (c.contains("allowed_origins")) {
                config.cors.allowed_origins = c["allowed_origins"].get<std::vector<std::string>>();
            }
            if (c.contains("allow_credentials")) config.cors.allow_credentials = c["allow_credentials"];
            if (c.contains("allowed_methods")) {
                config.cors.allowed_methods = c["allowed_methods"].get<std::vector<std::string>>();
            }
            if (c.contains("allowed_headers")) {
                config.cors.allowed_headers = c["allowed_headers"].get<std::vector<std::string>>();
            }
        }

        // Parse LLM config
        if (j.contains("llm")) {
            auto& l = j["llm"];
            if (l.contains("server_url")) config.llm.server_url = l["server_url"];
            if (l.contains("timeout")) config.llm.timeout = l["timeout"];
            if (l.contains("temperature")) config.llm.temperature = l["temperature"];
            if (l.contains("top_p")) config.llm.top_p = l["top_p"];
            if (l.contains("max_tokens")) config.llm.max_tokens = l["max_tokens"];
        }

        return config;
    }
};

// Global config instance
inline Config& get_config() {
    static Config config = Config::load();
    return config;
}

} // namespace prompt_portal

