#pragma once

#include "crow.h"
#include <nlohmann/json.hpp>

namespace prompt_portal {
namespace handlers {

class LeaderboardHandler {
public:
    // POST /api/leaderboard/submit
    static crow::response submit_maze_score(const crow::request& req);
    
    // POST /api/leaderboard/driving-game/submit
    static crow::response submit_driving_score(const crow::request& req);
    
    // GET /api/leaderboard
    static crow::response get_leaderboard(const crow::request& req);
    
    // GET /api/leaderboard/stats
    static crow::response get_stats();

private:
    static crow::response error_response(int status, const std::string& detail);
    static crow::response json_response(int status, const nlohmann::json& data);
};

} // namespace handlers
} // namespace prompt_portal

