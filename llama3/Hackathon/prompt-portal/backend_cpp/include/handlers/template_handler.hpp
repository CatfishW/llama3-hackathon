#pragma once

#include "crow.h"
#include <nlohmann/json.hpp>

namespace prompt_portal {
namespace handlers {

class TemplateHandler {
public:
    // POST /api/templates
    static crow::response create(const crow::request& req);
    
    // GET /api/templates
    static crow::response list(const crow::request& req);
    
    // GET /api/templates/{id}
    static crow::response get(const crow::request& req, int id);
    
    // GET /api/templates/public/{id}
    static crow::response get_public(int id);
    
    // PATCH /api/templates/{id}
    static crow::response update(const crow::request& req, int id);
    
    // DELETE /api/templates/{id}
    static crow::response remove(const crow::request& req, int id);

private:
    static crow::response error_response(int status, const std::string& detail);
    static crow::response json_response(int status, const nlohmann::json& data);
};

} // namespace handlers
} // namespace prompt_portal

