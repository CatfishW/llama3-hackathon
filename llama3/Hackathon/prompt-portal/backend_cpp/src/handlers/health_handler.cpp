#include "handlers/health_handler.hpp"
#include <chrono>
#include <ctime>
#include <iomanip>
#include <sstream>

namespace prompt_portal {
namespace handlers {

crow::response HealthHandler::json_response(int status, const nlohmann::json& data) {
    crow::response res(status, data.dump());
    res.set_header("Content-Type", "application/json");
    return res;
}

crow::response HealthHandler::health_check() {
    // Get current timestamp
    auto now = std::chrono::system_clock::now();
    auto time = std::chrono::system_clock::to_time_t(now);
    std::stringstream ss;
    ss << std::put_time(std::gmtime(&time), "%Y-%m-%dT%H:%M:%SZ");
    
    nlohmann::json result = {
        {"status", "healthy"},
        {"timestamp", ss.str()},
        {"backend", "cpp"},
        {"version", "1.0.0"},
        {"issues", nullptr}
    };
    
    return json_response(200, result);
}

} // namespace handlers
} // namespace prompt_portal
