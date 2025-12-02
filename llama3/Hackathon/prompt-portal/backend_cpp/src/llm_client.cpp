#include "llm_client.hpp"
#include <iostream>
#include <sstream>
#include <chrono>
#include <thread>
#include <cstring>

// Simple HTTP client using sockets
// For production, consider using libcurl or cpp-httplib

#ifdef _WIN32
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #pragma comment(lib, "ws2_32.lib")
    typedef SOCKET socket_t;
    #define SOCKET_ERROR_CODE SOCKET_ERROR
    #define INVALID_SOCKET_VAL INVALID_SOCKET
    #define CLOSE_SOCKET closesocket
#else
    #include <sys/socket.h>
    #include <netinet/in.h>
    #include <arpa/inet.h>
    #include <netdb.h>
    #include <unistd.h>
    typedef int socket_t;
    #define SOCKET_ERROR_CODE -1
    #define INVALID_SOCKET_VAL -1
    #define CLOSE_SOCKET close
#endif

namespace prompt_portal {

namespace {

struct UrlParts {
    std::string host;
    int port;
    std::string path;
};

UrlParts parse_url(const std::string& url) {
    UrlParts parts;
    parts.port = 80;
    parts.path = "/";
    
    std::string work = url;
    
    // Remove protocol
    if (work.find("http://") == 0) {
        work = work.substr(7);
    } else if (work.find("https://") == 0) {
        work = work.substr(8);
        parts.port = 443;
    }
    
    // Find path
    size_t path_pos = work.find('/');
    if (path_pos != std::string::npos) {
        parts.path = work.substr(path_pos);
        work = work.substr(0, path_pos);
    }
    
    // Find port
    size_t port_pos = work.find(':');
    if (port_pos != std::string::npos) {
        parts.port = std::stoi(work.substr(port_pos + 1));
        work = work.substr(0, port_pos);
    }
    
    parts.host = work;
    return parts;
}

std::string http_post(const std::string& url, const std::string& body, int timeout_sec = 300) {
    auto parts = parse_url(url);
    
    #ifdef _WIN32
    WSADATA wsaData;
    WSAStartup(MAKEWORD(2, 2), &wsaData);
    #endif
    
    socket_t sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock == INVALID_SOCKET_VAL) {
        throw std::runtime_error("Failed to create socket");
    }
    
    // Set timeout
    #ifdef _WIN32
    DWORD tv = timeout_sec * 1000;
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, (const char*)&tv, sizeof(tv));
    setsockopt(sock, SOL_SOCKET, SO_SNDTIMEO, (const char*)&tv, sizeof(tv));
    #else
    struct timeval tv;
    tv.tv_sec = timeout_sec;
    tv.tv_usec = 0;
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
    setsockopt(sock, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));
    #endif
    
    // Resolve hostname
    struct addrinfo hints = {}, *result;
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_STREAM;
    
    if (getaddrinfo(parts.host.c_str(), std::to_string(parts.port).c_str(), &hints, &result) != 0) {
        CLOSE_SOCKET(sock);
        throw std::runtime_error("Failed to resolve hostname: " + parts.host);
    }
    
    // Connect
    if (connect(sock, result->ai_addr, (int)result->ai_addrlen) == SOCKET_ERROR_CODE) {
        freeaddrinfo(result);
        CLOSE_SOCKET(sock);
        throw std::runtime_error("Failed to connect to " + parts.host + ":" + std::to_string(parts.port));
    }
    freeaddrinfo(result);
    
    // Build HTTP request
    std::ostringstream request;
    request << "POST " << parts.path << " HTTP/1.1\r\n";
    request << "Host: " << parts.host << ":" << parts.port << "\r\n";
    request << "Content-Type: application/json\r\n";
    request << "Content-Length: " << body.length() << "\r\n";
    request << "Connection: close\r\n";
    request << "\r\n";
    request << body;
    
    std::string req_str = request.str();
    send(sock, req_str.c_str(), (int)req_str.length(), 0);
    
    // Read response
    std::string response;
    char buffer[4096];
    int received;
    while ((received = recv(sock, buffer, sizeof(buffer) - 1, 0)) > 0) {
        buffer[received] = '\0';
        response += buffer;
    }
    
    CLOSE_SOCKET(sock);
    
    // Parse HTTP response
    size_t header_end = response.find("\r\n\r\n");
    if (header_end == std::string::npos) {
        throw std::runtime_error("Invalid HTTP response");
    }
    
    return response.substr(header_end + 4);
}

} // anonymous namespace

// =====================
// LLMClient Implementation
// =====================

LLMClient::LLMClient() {
    auto& config = get_config();
    server_url_ = config.llm.server_url;
    timeout_ = config.llm.timeout;
    default_temperature_ = config.llm.temperature;
    default_top_p_ = config.llm.top_p;
    default_max_tokens_ = config.llm.max_tokens;
    skip_thinking_ = true;
    available_ = test_connection();
}

LLMClient::LLMClient(const LlmConfig& config) {
    server_url_ = config.server_url;
    timeout_ = config.timeout;
    default_temperature_ = config.temperature;
    default_top_p_ = config.top_p;
    default_max_tokens_ = config.max_tokens;
    skip_thinking_ = true;
    available_ = test_connection();
}

bool LLMClient::test_connection() {
    try {
        std::cout << "[LLM] Testing connection to " << server_url_ << std::endl;
        
        nlohmann::json body = {
            {"model", "default"},
            {"messages", {{{"role", "system"}, {"content", "test"}}}},
            {"max_tokens", 1}
        };
        
        std::string response = http_post(server_url_ + "/v1/chat/completions", body.dump(), 10);
        auto json = nlohmann::json::parse(response);
        
        if (json.contains("choices")) {
            std::cout << "[LLM] Connection test successful" << std::endl;
            return true;
        }
    } catch (const std::exception& e) {
        std::cerr << "[LLM] Connection test failed: " << e.what() << std::endl;
    }
    return false;
}

std::string LLMClient::generate(
    const std::vector<ChatMessage>& messages,
    std::optional<double> temperature,
    std::optional<double> top_p,
    std::optional<int> max_tokens,
    const std::string& model
) {
    double temp = temperature.value_or(default_temperature_);
    double tp = top_p.value_or(default_top_p_);
    int mt = max_tokens.value_or(default_max_tokens_);
    
    // Build messages array
    nlohmann::json msgs = nlohmann::json::array();
    for (const auto& msg : messages) {
        msgs.push_back({{"role", msg.role}, {"content", msg.content}});
    }
    
    nlohmann::json body = {
        {"model", model},
        {"messages", msgs},
        {"temperature", temp},
        {"top_p", tp},
        {"max_tokens", mt}
    };
    
    if (skip_thinking_) {
        body["extra_body"] = {{"enable_thinking", false}};
    }
    
    try {
        auto start = std::chrono::steady_clock::now();
        
        std::string response = http_post(server_url_ + "/v1/chat/completions", body.dump(), timeout_);
        auto json = nlohmann::json::parse(response);
        
        auto end = std::chrono::steady_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
        
        if (json.contains("choices") && json["choices"].size() > 0) {
            std::string content = json["choices"][0]["message"]["content"].get<std::string>();
            std::cout << "[LLM] Generated response in " << duration.count() << "ms" << std::endl;
            return content;
        }
        
        throw std::runtime_error("Invalid response from LLM server");
        
    } catch (const nlohmann::json::exception& e) {
        throw std::runtime_error(std::string("JSON parse error: ") + e.what());
    } catch (const std::exception& e) {
        throw std::runtime_error(std::string("LLM generation failed: ") + e.what());
    }
}

void LLMClient::generate_stream(
    const std::vector<ChatMessage>& messages,
    std::function<void(const std::string&)> on_chunk,
    std::optional<double> temperature,
    std::optional<double> top_p,
    std::optional<int> max_tokens,
    const std::string& model
) {
    // For simplicity, use non-streaming and chunk the response
    // A full implementation would use SSE/chunked transfer encoding
    try {
        std::string full_response = generate(messages, temperature, top_p, max_tokens, model);
        
        // Simulate streaming by sending chunks
        const size_t chunk_size = 10;
        for (size_t i = 0; i < full_response.length(); i += chunk_size) {
            std::string chunk = full_response.substr(i, chunk_size);
            on_chunk(chunk);
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }
    } catch (const std::exception& e) {
        on_chunk(std::string("Error: ") + e.what());
    }
}

std::string LLMClient::make_request(const std::string& endpoint, const nlohmann::json& body) {
    return http_post(server_url_ + endpoint, body.dump(), timeout_);
}

// =====================
// SessionManager Implementation
// =====================

SessionManager::SessionManager(LLMClient& client, int max_history_messages)
    : client_(client), max_history_messages_(max_history_messages) {
    std::cout << "[SessionManager] Initialized with max_history_messages=" << max_history_messages << std::endl;
}

SessionManager::Session& SessionManager::get_or_create_session(
    const std::string& session_id, 
    const std::string& system_prompt
) {
    std::lock_guard<std::mutex> lock(sessions_mutex_);
    
    auto it = sessions_.find(session_id);
    if (it != sessions_.end()) {
        it->second.last_access = std::chrono::system_clock::now().time_since_epoch().count();
        return it->second;
    }
    
    // Create new session
    Session session;
    session.dialog.push_back({.role = "system", .content = system_prompt});
    session.created_at = std::chrono::system_clock::now().time_since_epoch().count();
    session.last_access = session.created_at;
    session.message_count = 0;
    
    sessions_[session_id] = std::move(session);
    std::cout << "[SessionManager] Created new session: " << session_id << std::endl;
    
    return sessions_[session_id];
}

void SessionManager::trim_history(Session& session) {
    // Keep system message + last N message pairs
    if (session.dialog.size() > 1) {
        int non_system = static_cast<int>(session.dialog.size()) - 1;
        int max_keep = max_history_messages_ * 2;  // User + assistant pairs
        
        if (non_system > max_keep) {
            // Keep system message and trim old messages
            std::vector<ChatMessage> new_dialog;
            new_dialog.push_back(session.dialog[0]);  // System message
            
            int start = static_cast<int>(session.dialog.size()) - max_keep;
            for (size_t i = start; i < session.dialog.size(); ++i) {
                new_dialog.push_back(session.dialog[i]);
            }
            
            session.dialog = std::move(new_dialog);
        }
    }
}

std::string SessionManager::process_message(
    const std::string& session_id,
    const std::string& system_prompt,
    const std::string& user_message,
    std::optional<double> temperature,
    std::optional<double> top_p,
    std::optional<int> max_tokens
) {
    Session* session_ptr;
    std::vector<ChatMessage> messages;
    
    {
        std::lock_guard<std::mutex> lock(sessions_mutex_);
        session_ptr = &get_or_create_session(session_id, system_prompt);
        
        // Add user message
        session_ptr->dialog.push_back({.role = "user", .content = user_message});
        session_ptr->message_count++;
        
        // Trim history
        trim_history(*session_ptr);
        
        // Copy messages for inference
        messages = session_ptr->dialog;
    }
    
    // Generate response (without holding lock)
    std::string response = client_.generate(messages, temperature, top_p, max_tokens);
    
    // Add assistant response to history
    {
        std::lock_guard<std::mutex> lock(sessions_mutex_);
        auto it = sessions_.find(session_id);
        if (it != sessions_.end()) {
            it->second.dialog.push_back({.role = "assistant", .content = response});
        }
    }
    
    return response;
}

void SessionManager::process_message_stream(
    const std::string& session_id,
    const std::string& system_prompt,
    const std::string& user_message,
    std::function<void(const std::string&)> on_chunk,
    std::optional<double> temperature,
    std::optional<double> top_p,
    std::optional<int> max_tokens
) {
    Session* session_ptr;
    std::vector<ChatMessage> messages;
    
    {
        std::lock_guard<std::mutex> lock(sessions_mutex_);
        session_ptr = &get_or_create_session(session_id, system_prompt);
        
        // Add user message
        session_ptr->dialog.push_back({.role = "user", .content = user_message});
        session_ptr->message_count++;
        
        // Trim history
        trim_history(*session_ptr);
        
        // Copy messages for inference
        messages = session_ptr->dialog;
    }
    
    // Collect full response
    std::string full_response;
    auto collector = [&](const std::string& chunk) {
        full_response += chunk;
        on_chunk(chunk);
    };
    
    // Generate streaming response (without holding lock)
    client_.generate_stream(messages, collector, temperature, top_p, max_tokens);
    
    // Add assistant response to history
    {
        std::lock_guard<std::mutex> lock(sessions_mutex_);
        auto it = sessions_.find(session_id);
        if (it != sessions_.end()) {
            it->second.dialog.push_back({.role = "assistant", .content = full_response});
        }
    }
}

std::optional<std::vector<ChatMessage>> SessionManager::get_session_history(const std::string& session_id) {
    std::lock_guard<std::mutex> lock(sessions_mutex_);
    
    auto it = sessions_.find(session_id);
    if (it != sessions_.end()) {
        return it->second.dialog;
    }
    return std::nullopt;
}

void SessionManager::clear_session(const std::string& session_id) {
    std::lock_guard<std::mutex> lock(sessions_mutex_);
    sessions_.erase(session_id);
    std::cout << "[SessionManager] Cleared session: " << session_id << std::endl;
}

// =====================
// Global instances
// =====================

static std::unique_ptr<LLMClient> g_llm_client;
static std::unique_ptr<SessionManager> g_session_manager;

void init_llm_service(const LlmConfig& config) {
    g_llm_client = std::make_unique<LLMClient>(config);
    g_session_manager = std::make_unique<SessionManager>(*g_llm_client, 20);
    std::cout << "[LLM] Service initialized with server: " << config.server_url << std::endl;
}

LLMClient& get_llm_client() {
    if (!g_llm_client) {
        // Initialize with default config
        g_llm_client = std::make_unique<LLMClient>();
    }
    return *g_llm_client;
}

SessionManager& get_session_manager() {
    if (!g_session_manager) {
        g_session_manager = std::make_unique<SessionManager>(get_llm_client(), 20);
    }
    return *g_session_manager;
}

} // namespace prompt_portal

