#include "handlers/leaderboard_handler.hpp"
#include "database.hpp"
#include "auth.hpp"
#include <iostream>

namespace prompt_portal {
namespace handlers {

crow::response LeaderboardHandler::error_response(int status, const std::string& detail) {
    nlohmann::json error = {{"detail", detail}};
    crow::response res(status, error.dump());
    res.set_header("Content-Type", "application/json");
    return res;
}

crow::response LeaderboardHandler::json_response(int status, const nlohmann::json& data) {
    crow::response res(status, data.dump());
    res.set_header("Content-Type", "application/json");
    return res;
}

crow::response LeaderboardHandler::submit_maze_score(const crow::request& req) {
    try {
        std::string auth_header = req.get_header_value("Authorization");
        auto user = Auth::instance().get_current_user(auth_header);
        
        if (!user) {
            return error_response(401, "Could not validate credentials");
        }
        
        auto body = nlohmann::json::parse(req.body);
        
        int template_id = body.value("template_id", 0);
        std::string session_id = body.value("session_id", "");
        std::string mode = body.value("mode", "manual");
        
        // Validate template exists
        auto tmpl = Database::instance().find_template_by_id(template_id);
        if (!tmpl) {
            return error_response(404, "Template not found");
        }
        
        if (tmpl->id == 0) { // This is just a dummy check to avoid compiler warnings if tmpl is unused
             // Template exists
        }
        
        if (mode != "lam" && mode != "manual") {
            mode = "manual";
        }
        
        Score score;
        score.user_id = user->id;
        score.template_id = template_id;
        score.session_id = session_id;
        score.score = body.value("score", 0.0);
        score.mode = mode;
        score.survival_time = body.value("survival_time", 0.0);
        score.oxygen_collected = body.value("oxygen_collected", 0);
        score.germs = body.value("germs", 0);
        
        if (body.contains("new_score") && !body["new_score"].is_null()) {
            score.new_score = body["new_score"].get<double>();
        }
        if (body.contains("total_steps") && !body["total_steps"].is_null()) {
            score.total_steps = body["total_steps"].get<int>();
        }
        if (body.contains("optimal_steps") && !body["optimal_steps"].is_null()) {
            score.optimal_steps = body["optimal_steps"].get<int>();
        }
        if (body.contains("backtrack_count") && !body["backtrack_count"].is_null()) {
            score.backtrack_count = body["backtrack_count"].get<int>();
        }
        if (body.contains("collision_count") && !body["collision_count"].is_null()) {
            score.collision_count = body["collision_count"].get<int>();
        }
        if (body.contains("dead_end_entries") && !body["dead_end_entries"].is_null()) {
            score.dead_end_entries = body["dead_end_entries"].get<int>();
        }
        if (body.contains("avg_latency_ms") && !body["avg_latency_ms"].is_null()) {
            score.avg_latency_ms = body["avg_latency_ms"].get<double>();
        }
        
        Score result = Database::instance().create_score(score);
        
        std::cout << "[Leaderboard] Maze score submitted - User: " << user->id 
                  << ", Score: " << result.score << ", Mode: " << mode << std::endl;
        
        return json_response(201, result.to_json());
        
    } catch (const std::exception& e) {
        std::cerr << "[Leaderboard] Submit maze score error: " << e.what() << std::endl;
        return error_response(500, "Internal server error");
    }
}

crow::response LeaderboardHandler::get_leaderboard(const crow::request& req) {
    try {
        // Parse query parameters
        int limit = 20;
        int skip = 0;
        std::string mode;
        
        auto limit_param = req.url_params.get("limit");
        auto skip_param = req.url_params.get("skip");
        auto mode_param = req.url_params.get("mode");
        
        if (limit_param) limit = std::stoi(limit_param);
        if (skip_param) skip = std::stoi(skip_param);
        if (mode_param) mode = mode_param;
        
        std::cout << "[Leaderboard] Query - mode: " << mode << ", limit: " << limit << ", skip: " << skip << std::endl;
        
        nlohmann::json result = nlohmann::json::array();
        
        // Maze game leaderboard
        auto entries = Database::instance().get_leaderboard(limit, skip, mode);
        for (const auto& entry : entries) {
            result.push_back(entry.to_json());
        }
        
        int total = Database::instance().count_scores();
        crow::response res(200, result.dump());
        res.set_header("Content-Type", "application/json");
        res.set_header("X-Total-Count", std::to_string(total));
        return res;
        
    } catch (const std::exception& e) {
        std::cerr << "[Leaderboard] Get leaderboard error: " << e.what() << std::endl;
        return error_response(500, "Internal server error");
    }
}

crow::response LeaderboardHandler::get_stats() {
    try {
        int participants = Database::instance().count_participants();
        int registered_users = Database::instance().count_users();
        
        nlohmann::json result = {
            {"participants", participants},
            {"registered_users", registered_users}
        };
        
        return json_response(200, result);
        
    } catch (const std::exception& e) {
        std::cerr << "[Leaderboard] Get stats error: " << e.what() << std::endl;
        return error_response(500, "Internal server error");
    }
}

} // namespace handlers
} // namespace prompt_portal

