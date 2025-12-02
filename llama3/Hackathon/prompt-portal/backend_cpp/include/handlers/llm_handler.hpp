#pragma once

#include "crow.h"
#include <nlohmann/json.hpp>

namespace prompt_portal {
namespace handlers {

class LLMHandler {
public:
    // POST /api/llm/chat - Single-shot chat completion
    static crow::response chat(const crow::request& req);
    
    // POST /api/llm/chat/session - Session-based chat
    static crow::response session_chat(const crow::request& req);
    
    // POST /api/llm/chat/stream - Streaming chat (SSE)
    static crow::response chat_stream(const crow::request& req);
    
    // POST /api/llm/chat/session/stream - Session streaming chat (SSE)
    static crow::response session_chat_stream(const crow::request& req);
    
    // GET /api/llm/chat/session/{session_id}/history
    static crow::response get_session_history(const crow::request& req, const std::string& session_id);
    
    // POST /api/llm/chat/session/history - Alternative POST endpoint
    static crow::response post_session_history(const crow::request& req);
    
    // DELETE /api/llm/chat/session/{session_id}
    static crow::response clear_session(const crow::request& req, const std::string& session_id);
    
    // GET /api/llm/health - LLM service health
    static crow::response health();

private:
    static crow::response error_response(int status, const std::string& detail);
    static crow::response json_response(int status, const nlohmann::json& data);
};

} // namespace handlers
} // namespace prompt_portal

