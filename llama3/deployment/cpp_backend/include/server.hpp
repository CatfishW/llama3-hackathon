#pragma once

#include <httplib.h>
#include <string>
#include <memory>

namespace openai_proxy {

/**
 * OpenAI-compatible HTTP server.
 * Proxies requests to llama.cpp backend.
 */
class Server {
public:
    Server();
    ~Server();
    
    // Start server (blocking)
    void run(const std::string& host, int port);
    
    // Stop server
    void stop();
    
private:
    // Register all routes
    void setup_routes();
    
    // Add CORS headers to response
    void add_cors_headers(httplib::Response& res);
    
    // Route handlers
    void handle_root(const httplib::Request& req, httplib::Response& res);
    void handle_health(const httplib::Request& req, httplib::Response& res);
    void handle_models(const httplib::Request& req, httplib::Response& res);
    void handle_chat_completions(const httplib::Request& req, httplib::Response& res);
    void handle_completions(const httplib::Request& req, httplib::Response& res);
    void handle_options(const httplib::Request& req, httplib::Response& res);
    
    std::unique_ptr<httplib::Server> server_;
};

} // namespace openai_proxy

