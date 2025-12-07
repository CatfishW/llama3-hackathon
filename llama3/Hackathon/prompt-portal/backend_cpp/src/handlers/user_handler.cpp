#include "handlers/user_handler.hpp"
#include "database.hpp"
#include "auth.hpp"
#include <iostream>

namespace prompt_portal {
namespace handlers {

crow::response UserHandler::error_response(int status, const std::string& detail) {
    nlohmann::json error = {{"detail", detail}};
    crow::response res(status, error.dump());
    res.set_header("Content-Type", "application/json");
    return res;
}

crow::response UserHandler::json_response(int status, const nlohmann::json& data) {
    crow::response res(status, data.dump());
    res.set_header("Content-Type", "application/json");
    return res;
}

crow::response UserHandler::get_current_user(const crow::request& req) {
    try {
        std::string auth_header = req.get_header_value("Authorization");
        auto user = Auth::instance().get_current_user(auth_header);
        
        if (!user) {
            return error_response(401, "Could not validate credentials");
        }
        
        return json_response(200, user->to_json());
        
    } catch (const std::exception& e) {
        std::cerr << "[Users] Get current user error: " << e.what() << std::endl;
        return error_response(500, "Internal server error");
    }
}

crow::response UserHandler::search(const crow::request& req) {
    try {
        std::string auth_header = req.get_header_value("Authorization");
        auto user = Auth::instance().get_current_user(auth_header);
        
        if (!user) {
            return error_response(401, "Could not validate credentials");
        }
        
        auto query_param = req.url_params.get("q");
        std::string query = query_param ? query_param : "";
        
        int limit = 20;
        auto limit_param = req.url_params.get("limit");
        if (limit_param) limit = std::stoi(limit_param);
        
        auto users = Database::instance().search_users(query, limit);
        
        nlohmann::json result = nlohmann::json::array();
        for (const auto& u : users) {
            nlohmann::json user_json = {
                {"id", u.id},
                {"email", u.email},
                {"full_name", u.full_name.value_or("")},
                {"profile_picture", u.profile_picture.value_or("")},
                {"level", u.level},
                {"is_online", u.is_online},
                {"has_pending_request", false}
            };
            result.push_back(user_json);
        }
        
        return json_response(200, result);
        
    } catch (const std::exception& e) {
        std::cerr << "[Users] Search error: " << e.what() << std::endl;
        return error_response(500, "Internal server error");
    }
}

crow::response UserHandler::get_by_id(int id) {
    try {
        auto user = Database::instance().find_user_by_id(id);
        
        if (!user) {
            return error_response(404, "User not found");
        }
        
        return json_response(200, user->to_json());
        
    } catch (const std::exception& e) {
        std::cerr << "[Users] Get by ID error: " << e.what() << std::endl;
        return error_response(500, "Internal server error");
    }
}

} // namespace handlers
} // namespace prompt_portal

