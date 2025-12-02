#include "handlers/llm_handler.hpp"
#include "llm_client.hpp"
#include "auth.hpp"
#include <iostream>
#include <sstream>

namespace prompt_portal {
namespace handlers {

crow::response LLMHandler::error_response(int status, const std::string& detail) {
    nlohmann::json error = {{"detail", detail}};
    crow::response res(status, error.dump());
    res.set_header("Content-Type", "application/json");
    return res;
}

crow::response LLMHandler::json_response(int status, const nlohmann::json& data) {
    crow::response res(status, data.dump());
    res.set_header("Content-Type", "application/json");
    return res;
}

crow::response LLMHandler::chat(const crow::request& req) {
    try {
        // Authenticate user
        std::string auth_header = req.get_header_value("Authorization");
        auto user = Auth::instance().get_current_user(auth_header);
        
        if (!user) {
            return error_response(401, "Could not validate credentials");
        }
        
        auto body = nlohmann::json::parse(req.body);
        
        // Parse messages
        if (!body.contains("messages") || !body["messages"].is_array()) {
            return error_response(400, "messages array is required");
        }
        
        std::vector<ChatMessage> messages;
        for (const auto& msg : body["messages"]) {
            ChatMessage cm;
            cm.role = msg.value("role", "user");
            cm.content = msg.value("content", "");
            messages.push_back(cm);
        }
        
        if (messages.empty()) {
            return error_response(400, "At least one message is required");
        }
        
        // Optional parameters
        std::optional<double> temperature;
        std::optional<double> top_p;
        std::optional<int> max_tokens;
        
        if (body.contains("temperature") && !body["temperature"].is_null()) {
            temperature = body["temperature"].get<double>();
        }
        if (body.contains("top_p") && !body["top_p"].is_null()) {
            top_p = body["top_p"].get<double>();
        }
        if (body.contains("max_tokens") && !body["max_tokens"].is_null()) {
            max_tokens = body["max_tokens"].get<int>();
        }
        
        std::string model = body.value("model", "default");
        
        // Generate response
        auto& client = get_llm_client();
        std::string response = client.generate(messages, temperature, top_p, max_tokens, model);
        
        nlohmann::json result = {
            {"response", response}
        };
        
        return json_response(200, result);
        
    } catch (const std::runtime_error& e) {
        std::cerr << "[LLM] Chat error: " << e.what() << std::endl;
        return error_response(503, e.what());
    } catch (const std::exception& e) {
        std::cerr << "[LLM] Chat error: " << e.what() << std::endl;
        return error_response(500, "Internal server error");
    }
}

crow::response LLMHandler::session_chat(const crow::request& req) {
    try {
        // Authenticate user
        std::string auth_header = req.get_header_value("Authorization");
        auto user = Auth::instance().get_current_user(auth_header);
        
        if (!user) {
            return error_response(401, "Could not validate credentials");
        }
        
        auto body = nlohmann::json::parse(req.body);
        
        std::string session_id = body.value("session_id", "");
        std::string message = body.value("message", "");
        std::string system_prompt = body.value("system_prompt", "You are a helpful AI assistant.");
        
        if (session_id.empty()) {
            return error_response(400, "session_id is required");
        }
        if (message.empty()) {
            return error_response(400, "message is required");
        }
        
        // Optional parameters
        std::optional<double> temperature;
        std::optional<double> top_p;
        std::optional<int> max_tokens;
        
        if (body.contains("temperature") && !body["temperature"].is_null()) {
            temperature = body["temperature"].get<double>();
        }
        if (body.contains("top_p") && !body["top_p"].is_null()) {
            top_p = body["top_p"].get<double>();
        }
        if (body.contains("max_tokens") && !body["max_tokens"].is_null()) {
            max_tokens = body["max_tokens"].get<int>();
        }
        
        // Process message with session
        auto& session_manager = get_session_manager();
        std::string response = session_manager.process_message(
            session_id, system_prompt, message, temperature, top_p, max_tokens
        );
        
        nlohmann::json result = {
            {"response", response},
            {"session_id", session_id}
        };
        
        return json_response(200, result);
        
    } catch (const std::runtime_error& e) {
        std::cerr << "[LLM] Session chat error: " << e.what() << std::endl;
        return error_response(503, e.what());
    } catch (const std::exception& e) {
        std::cerr << "[LLM] Session chat error: " << e.what() << std::endl;
        return error_response(500, "Internal server error");
    }
}

crow::response LLMHandler::chat_stream(const crow::request& req) {
    try {
        // Authenticate user
        std::string auth_header = req.get_header_value("Authorization");
        auto user = Auth::instance().get_current_user(auth_header);
        
        if (!user) {
            return error_response(401, "Could not validate credentials");
        }
        
        auto body = nlohmann::json::parse(req.body);
        
        // Parse messages
        if (!body.contains("messages") || !body["messages"].is_array()) {
            return error_response(400, "messages array is required");
        }
        
        std::vector<ChatMessage> messages;
        for (const auto& msg : body["messages"]) {
            ChatMessage cm;
            cm.role = msg.value("role", "user");
            cm.content = msg.value("content", "");
            messages.push_back(cm);
        }
        
        // Optional parameters
        std::optional<double> temperature;
        std::optional<double> top_p;
        std::optional<int> max_tokens;
        
        if (body.contains("temperature") && !body["temperature"].is_null()) {
            temperature = body["temperature"].get<double>();
        }
        if (body.contains("top_p") && !body["top_p"].is_null()) {
            top_p = body["top_p"].get<double>();
        }
        if (body.contains("max_tokens") && !body["max_tokens"].is_null()) {
            max_tokens = body["max_tokens"].get<int>();
        }
        
        std::string model = body.value("model", "default");
        
        // Generate response (for now, non-streaming wrapped as SSE)
        auto& client = get_llm_client();
        
        std::ostringstream sse_stream;
        
        client.generate_stream(messages, [&sse_stream](const std::string& chunk) {
            nlohmann::json chunk_data = {{"content", chunk}};
            sse_stream << "data: " << chunk_data.dump() << "\n\n";
        }, temperature, top_p, max_tokens, model);
        
        // Send done signal
        nlohmann::json done = {{"done", true}};
        sse_stream << "data: " << done.dump() << "\n\n";
        
        crow::response res(200, sse_stream.str());
        res.set_header("Content-Type", "text/event-stream");
        res.set_header("Cache-Control", "no-cache");
        res.set_header("Connection", "keep-alive");
        return res;
        
    } catch (const std::runtime_error& e) {
        std::cerr << "[LLM] Stream error: " << e.what() << std::endl;
        return error_response(503, e.what());
    } catch (const std::exception& e) {
        std::cerr << "[LLM] Stream error: " << e.what() << std::endl;
        return error_response(500, "Internal server error");
    }
}

crow::response LLMHandler::session_chat_stream(const crow::request& req) {
    try {
        // Authenticate user
        std::string auth_header = req.get_header_value("Authorization");
        auto user = Auth::instance().get_current_user(auth_header);
        
        if (!user) {
            return error_response(401, "Could not validate credentials");
        }
        
        auto body = nlohmann::json::parse(req.body);
        
        std::string session_id = body.value("session_id", "");
        std::string message = body.value("message", "");
        std::string system_prompt = body.value("system_prompt", "You are a helpful AI assistant.");
        
        if (session_id.empty() || message.empty()) {
            return error_response(400, "session_id and message are required");
        }
        
        // Optional parameters
        std::optional<double> temperature;
        std::optional<double> top_p;
        std::optional<int> max_tokens;
        
        if (body.contains("temperature") && !body["temperature"].is_null()) {
            temperature = body["temperature"].get<double>();
        }
        if (body.contains("top_p") && !body["top_p"].is_null()) {
            top_p = body["top_p"].get<double>();
        }
        if (body.contains("max_tokens") && !body["max_tokens"].is_null()) {
            max_tokens = body["max_tokens"].get<int>();
        }
        
        auto& session_manager = get_session_manager();
        
        std::ostringstream sse_stream;
        
        session_manager.process_message_stream(
            session_id, system_prompt, message,
            [&sse_stream, &session_id](const std::string& chunk) {
                nlohmann::json chunk_data = {{"content", chunk}, {"session_id", session_id}};
                sse_stream << "data: " << chunk_data.dump() << "\n\n";
            },
            temperature, top_p, max_tokens
        );
        
        // Send done signal
        nlohmann::json done = {{"done", true}, {"session_id", session_id}};
        sse_stream << "data: " << done.dump() << "\n\n";
        
        crow::response res(200, sse_stream.str());
        res.set_header("Content-Type", "text/event-stream");
        res.set_header("Cache-Control", "no-cache");
        res.set_header("Connection", "keep-alive");
        return res;
        
    } catch (const std::runtime_error& e) {
        std::cerr << "[LLM] Session stream error: " << e.what() << std::endl;
        return error_response(503, e.what());
    } catch (const std::exception& e) {
        std::cerr << "[LLM] Session stream error: " << e.what() << std::endl;
        return error_response(500, "Internal server error");
    }
}

crow::response LLMHandler::get_session_history(const crow::request& req, const std::string& session_id) {
    try {
        // Authenticate user
        std::string auth_header = req.get_header_value("Authorization");
        auto user = Auth::instance().get_current_user(auth_header);
        
        if (!user) {
            return error_response(401, "Could not validate credentials");
        }
        
        auto& session_manager = get_session_manager();
        auto history = session_manager.get_session_history(session_id);
        
        if (!history) {
            return error_response(404, "Session not found");
        }
        
        nlohmann::json messages = nlohmann::json::array();
        for (const auto& msg : *history) {
            messages.push_back({{"role", msg.role}, {"content", msg.content}});
        }
        
        nlohmann::json result = {
            {"session_id", session_id},
            {"messages", messages}
        };
        
        return json_response(200, result);
        
    } catch (const std::exception& e) {
        std::cerr << "[LLM] Get history error: " << e.what() << std::endl;
        return error_response(500, "Internal server error");
    }
}

crow::response LLMHandler::post_session_history(const crow::request& req) {
    try {
        // Authenticate user
        std::string auth_header = req.get_header_value("Authorization");
        auto user = Auth::instance().get_current_user(auth_header);
        
        if (!user) {
            return error_response(401, "Could not validate credentials");
        }
        
        auto body = nlohmann::json::parse(req.body);
        std::string session_id = body.value("session_id", "");
        
        if (session_id.empty()) {
            return error_response(400, "session_id is required");
        }
        
        auto& session_manager = get_session_manager();
        auto history = session_manager.get_session_history(session_id);
        
        if (!history) {
            return error_response(404, "Session not found");
        }
        
        nlohmann::json messages = nlohmann::json::array();
        for (const auto& msg : *history) {
            messages.push_back({{"role", msg.role}, {"content", msg.content}});
        }
        
        nlohmann::json result = {
            {"session_id", session_id},
            {"messages", messages}
        };
        
        return json_response(200, result);
        
    } catch (const std::exception& e) {
        std::cerr << "[LLM] Post history error: " << e.what() << std::endl;
        return error_response(500, "Internal server error");
    }
}

crow::response LLMHandler::clear_session(const crow::request& req, const std::string& session_id) {
    try {
        // Authenticate user
        std::string auth_header = req.get_header_value("Authorization");
        auto user = Auth::instance().get_current_user(auth_header);
        
        if (!user) {
            return error_response(401, "Could not validate credentials");
        }
        
        auto& session_manager = get_session_manager();
        session_manager.clear_session(session_id);
        
        nlohmann::json result = {
            {"ok", true},
            {"message", "Session " + session_id + " cleared"}
        };
        
        return json_response(200, result);
        
    } catch (const std::exception& e) {
        std::cerr << "[LLM] Clear session error: " << e.what() << std::endl;
        return error_response(500, "Internal server error");
    }
}

crow::response LLMHandler::health() {
    try {
        auto& client = get_llm_client();
        
        nlohmann::json result = {
            {"status", client.is_available() ? "ok" : "unavailable"},
            {"server_url", client.server_url()},
            {"temperature", client.default_temperature()},
            {"max_tokens", client.default_max_tokens()}
        };
        
        int status = client.is_available() ? 200 : 503;
        return json_response(status, result);
        
    } catch (const std::exception& e) {
        std::cerr << "[LLM] Health check error: " << e.what() << std::endl;
        return error_response(503, "LLM service not initialized");
    }
}

} // namespace handlers
} // namespace prompt_portal

