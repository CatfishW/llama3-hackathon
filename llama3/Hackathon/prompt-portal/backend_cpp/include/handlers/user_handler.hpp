#pragma once

#include "crow.h"
#include <nlohmann/json.hpp>

namespace prompt_portal {
namespace handlers {

class UserHandler {
public:
    // GET /api/users/me
    static crow::response get_current_user(const crow::request& req);
    
    // GET /api/users/search
    static crow::response search(const crow::request& req);
    
    // GET /api/users/{id}
    static crow::response get_by_id(int id);

private:
    static crow::response error_response(int status, const std::string& detail);
    static crow::response json_response(int status, const nlohmann::json& data);
};

} // namespace handlers
} // namespace prompt_portal

