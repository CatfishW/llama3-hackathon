#include "crow.h"
#include "config.hpp"
#include "database.hpp"
#include "auth.hpp"
#include "llm_client.hpp"
#include "handlers/auth_handler.hpp"
#include "handlers/template_handler.hpp"
#include "handlers/leaderboard_handler.hpp"
#include "handlers/health_handler.hpp"
#include "handlers/user_handler.hpp"
#include "handlers/llm_handler.hpp"
#include <iostream>
#include <filesystem>

using namespace prompt_portal;
using namespace prompt_portal::handlers;

int main(int argc, char* argv[]) {
    std::cout << R"(
  ____                            _     ____            _        _    
 |  _ \ _ __ ___  _ __ ___  _ __ | |_  |  _ \ ___  _ __| |_ __ _| |   
 | |_) | '__/ _ \| '_ ` _ \| '_ \| __| | |_) / _ \| '__| __/ _` | |   
 |  __/| | | (_) | | | | | | |_) | |_  |  __/ (_) | |  | || (_| | |   
 |_|   |_|  \___/|_| |_| |_| .__/ \__| |_|   \___/|_|   \__\__,_|_|   
                           |_|                                         
                    C++ Backend v1.0.0 (Crow Framework)
    )" << std::endl;

    // Load configuration
    std::string config_path = "config.json";
    if (argc > 1) {
        config_path = argv[1];
    }
    
    std::cout << "[Main] Loading configuration from: " << config_path << std::endl;
    
    // Initialize database
    std::cout << "[Main] Initializing database..." << std::endl;
    Database::instance().initialize();
    
    // Initialize LLM service
    std::cout << "[Main] Initializing LLM service..." << std::endl;
    init_llm_service(config.llm);
    
    // Create uploads directory
    std::filesystem::create_directories("uploads");
    
    // Create Crow application
    crow::SimpleApp app;
    
    auto& config = get_config();

    // ========================
    // CORS Preflight Handler
    // ========================
    CROW_ROUTE(app, "/<path>").methods(crow::HTTPMethod::OPTIONS)
    ([](const crow::request& req, const std::string& path) {
        crow::response res(204);
        std::string origin = req.get_header_value("Origin");
        if (origin.empty()) origin = "*";
        
        res.add_header("Access-Control-Allow-Origin", origin);
        res.add_header("Access-Control-Allow-Credentials", "true");
        res.add_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS,PATCH");
        res.add_header("Access-Control-Allow-Headers", 
            req.get_header_value("Access-Control-Request-Headers").empty() 
            ? "*" : req.get_header_value("Access-Control-Request-Headers"));
        if (origin != "*") {
            res.add_header("Vary", "Origin");
        }
        return res;
    });

    // Helper to add CORS headers to responses
    auto add_cors = [](crow::response& res, const crow::request& req) {
        std::string origin = req.get_header_value("Origin");
        if (origin.empty()) origin = "*";
        res.add_header("Access-Control-Allow-Origin", origin);
        res.add_header("Access-Control-Allow-Credentials", "true");
        if (origin != "*") {
            res.add_header("Vary", "Origin");
        }
    };

    // ========================
    // Auth Routes
    // ========================
    CROW_ROUTE(app, "/api/auth/register").methods(crow::HTTPMethod::POST)
    ([&](const crow::request& req) {
        auto res = AuthHandler::register_user(req);
        add_cors(res, req);
        return res;
    });

    CROW_ROUTE(app, "/api/auth/login").methods(crow::HTTPMethod::POST)
    ([&](const crow::request& req) {
        auto res = AuthHandler::login(req);
        add_cors(res, req);
        return res;
    });

    CROW_ROUTE(app, "/api/auth/change-password").methods(crow::HTTPMethod::POST)
    ([&](const crow::request& req) {
        auto res = AuthHandler::change_password(req);
        add_cors(res, req);
        return res;
    });

    CROW_ROUTE(app, "/api/auth/account").methods(crow::HTTPMethod::DELETE)
    ([&](const crow::request& req) {
        auto res = AuthHandler::delete_account(req);
        add_cors(res, req);
        return res;
    });

    // ========================
    // User Routes
    // ========================
    CROW_ROUTE(app, "/api/users/me").methods(crow::HTTPMethod::GET)
    ([&](const crow::request& req) {
        auto res = UserHandler::get_current_user(req);
        add_cors(res, req);
        return res;
    });

    CROW_ROUTE(app, "/api/users/search").methods(crow::HTTPMethod::GET)
    ([&](const crow::request& req) {
        auto res = UserHandler::search(req);
        add_cors(res, req);
        return res;
    });

    CROW_ROUTE(app, "/api/users/<int>").methods(crow::HTTPMethod::GET)
    ([&](const crow::request& req, int id) {
        auto res = UserHandler::get_by_id(id);
        add_cors(res, req);
        return res;
    });

    // ========================
    // Template Routes
    // ========================
    CROW_ROUTE(app, "/api/templates").methods(crow::HTTPMethod::POST)
    ([&](const crow::request& req) {
        auto res = TemplateHandler::create(req);
        add_cors(res, req);
        return res;
    });

    CROW_ROUTE(app, "/api/templates/").methods(crow::HTTPMethod::POST)
    ([&](const crow::request& req) {
        auto res = TemplateHandler::create(req);
        add_cors(res, req);
        return res;
    });

    CROW_ROUTE(app, "/api/templates").methods(crow::HTTPMethod::GET)
    ([&](const crow::request& req) {
        auto res = TemplateHandler::list(req);
        add_cors(res, req);
        return res;
    });

    CROW_ROUTE(app, "/api/templates/").methods(crow::HTTPMethod::GET)
    ([&](const crow::request& req) {
        auto res = TemplateHandler::list(req);
        add_cors(res, req);
        return res;
    });

    CROW_ROUTE(app, "/api/templates/<int>").methods(crow::HTTPMethod::GET)
    ([&](const crow::request& req, int id) {
        auto res = TemplateHandler::get(req, id);
        add_cors(res, req);
        return res;
    });

    CROW_ROUTE(app, "/api/templates/public/<int>").methods(crow::HTTPMethod::GET)
    ([&](const crow::request& req, int id) {
        auto res = TemplateHandler::get_public(id);
        add_cors(res, req);
        return res;
    });

    CROW_ROUTE(app, "/api/templates/<int>").methods(crow::HTTPMethod::PATCH)
    ([&](const crow::request& req, int id) {
        auto res = TemplateHandler::update(req, id);
        add_cors(res, req);
        return res;
    });

    CROW_ROUTE(app, "/api/templates/<int>").methods(crow::HTTPMethod::DELETE)
    ([&](const crow::request& req, int id) {
        auto res = TemplateHandler::remove(req, id);
        add_cors(res, req);
        return res;
    });

    // ========================
    // Leaderboard Routes
    // ========================
    CROW_ROUTE(app, "/api/leaderboard/submit").methods(crow::HTTPMethod::POST)
    ([&](const crow::request& req) {
        auto res = LeaderboardHandler::submit_maze_score(req);
        add_cors(res, req);
        return res;
    });

    CROW_ROUTE(app, "/api/leaderboard/driving-game/submit").methods(crow::HTTPMethod::POST)
    ([&](const crow::request& req) {
        auto res = LeaderboardHandler::submit_driving_score(req);
        add_cors(res, req);
        return res;
    });

    CROW_ROUTE(app, "/api/leaderboard").methods(crow::HTTPMethod::GET)
    ([&](const crow::request& req) {
        auto res = LeaderboardHandler::get_leaderboard(req);
        add_cors(res, req);
        return res;
    });

    CROW_ROUTE(app, "/api/leaderboard/").methods(crow::HTTPMethod::GET)
    ([&](const crow::request& req) {
        auto res = LeaderboardHandler::get_leaderboard(req);
        add_cors(res, req);
        return res;
    });

    CROW_ROUTE(app, "/api/leaderboard/stats").methods(crow::HTTPMethod::GET)
    ([&](const crow::request& req) {
        auto res = LeaderboardHandler::get_stats();
        add_cors(res, req);
        return res;
    });

    // ========================
    // Health Routes
    // ========================
    CROW_ROUTE(app, "/api/health").methods(crow::HTTPMethod::GET)
    ([&](const crow::request& req) {
        auto res = HealthHandler::health_check();
        add_cors(res, req);
        return res;
    });

    CROW_ROUTE(app, "/api/health/").methods(crow::HTTPMethod::GET)
    ([&](const crow::request& req) {
        auto res = HealthHandler::health_check();
        add_cors(res, req);
        return res;
    });

    // ========================
    // LLM Routes
    // ========================
    CROW_ROUTE(app, "/api/llm/chat").methods(crow::HTTPMethod::POST)
    ([&](const crow::request& req) {
        auto res = LLMHandler::chat(req);
        add_cors(res, req);
        return res;
    });

    CROW_ROUTE(app, "/api/llm/chat/session").methods(crow::HTTPMethod::POST)
    ([&](const crow::request& req) {
        auto res = LLMHandler::session_chat(req);
        add_cors(res, req);
        return res;
    });

    CROW_ROUTE(app, "/api/llm/chat/stream").methods(crow::HTTPMethod::POST)
    ([&](const crow::request& req) {
        auto res = LLMHandler::chat_stream(req);
        add_cors(res, req);
        return res;
    });

    CROW_ROUTE(app, "/api/llm/chat/session/stream").methods(crow::HTTPMethod::POST)
    ([&](const crow::request& req) {
        auto res = LLMHandler::session_chat_stream(req);
        add_cors(res, req);
        return res;
    });

    CROW_ROUTE(app, "/api/llm/chat/session/<string>/history").methods(crow::HTTPMethod::GET)
    ([&](const crow::request& req, const std::string& session_id) {
        auto res = LLMHandler::get_session_history(req, session_id);
        add_cors(res, req);
        return res;
    });

    CROW_ROUTE(app, "/api/llm/chat/session/history").methods(crow::HTTPMethod::POST)
    ([&](const crow::request& req) {
        auto res = LLMHandler::post_session_history(req);
        add_cors(res, req);
        return res;
    });

    CROW_ROUTE(app, "/api/llm/chat/session/<string>").methods(crow::HTTPMethod::DELETE)
    ([&](const crow::request& req, const std::string& session_id) {
        auto res = LLMHandler::clear_session(req, session_id);
        add_cors(res, req);
        return res;
    });

    CROW_ROUTE(app, "/api/llm/health").methods(crow::HTTPMethod::GET)
    ([&](const crow::request& req) {
        auto res = LLMHandler::health();
        add_cors(res, req);
        return res;
    });

    // ========================
    // Root Route
    // ========================
    CROW_ROUTE(app, "/")
    ([&](const crow::request& req) {
        crow::response res(200, R"({
            "name": "Prompt Portal C++ Backend",
            "version": "1.0.0",
            "framework": "Crow",
            "status": "running"
        })");
        res.set_header("Content-Type", "application/json");
        add_cors(res, req);
        return res;
    });

    // ========================
    // Start Server
    // ========================
    std::cout << "\n[Main] Starting server on " << config.server.host 
              << ":" << config.server.port << std::endl;
    std::cout << "[Main] Press Ctrl+C to stop\n" << std::endl;

    app.port(config.server.port)
       .multithreaded()
       .run();

    return 0;
}

