#pragma once

#include "crow.h"
#include <nlohmann/json.hpp>

namespace prompt_portal {
namespace handlers {

class HealthHandler {
public:
    // GET /api/health
    static crow::response health_check();

private:
    static crow::response json_response(int status, const nlohmann::json& data);
};

} // namespace handlers
} // namespace prompt_portal

