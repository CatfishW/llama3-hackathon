#pragma once

#include "crow.h"
#include <nlohmann/json.hpp>

namespace prompt_portal {
namespace handlers {

class AuthHandler {
public:
    // POST /api/auth/register
    static crow::response register_user(const crow::request& req);
    
    // POST /api/auth/login
    static crow::response login(const crow::request& req);
    
    // POST /api/auth/change-password
    static crow::response change_password(const crow::request& req);
    
    // DELETE /api/auth/account
    static crow::response delete_account(const crow::request& req);

private:
    static crow::response error_response(int status, const std::string& detail);
    static crow::response json_response(int status, const nlohmann::json& data);
};

} // namespace handlers
} // namespace prompt_portal

