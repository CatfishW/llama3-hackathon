#pragma once

#include <string>
#include <vector>
#include "crow.h"
#include "../config.hpp"

namespace prompt_portal {
namespace middleware {

struct CorsMiddleware {
    struct context {};

    CorsMiddleware() {
        auto& config = get_config();
        allowed_origins_ = config.cors.allowed_origins;
        allow_credentials_ = config.cors.allow_credentials;
        allowed_methods_ = join(config.cors.allowed_methods, ", ");
        allowed_headers_ = config.cors.allowed_headers.empty() ? "*" : join(config.cors.allowed_headers, ", ");
    }

    void before_handle(crow::request& req, crow::response& res, context& ctx) {
        // Allow all origins in development (or check against allowed list)
        std::string origin = req.get_header_value("Origin");
        if (origin.empty()) {
            origin = "*";
        }
        
        res.add_header("Access-Control-Allow-Origin", origin);
        res.add_header("Access-Control-Allow-Credentials", allow_credentials_ ? "true" : "false");
        res.add_header("Access-Control-Allow-Methods", allowed_methods_);
        res.add_header("Access-Control-Allow-Headers", allowed_headers_);
        res.add_header("Access-Control-Expose-Headers", "*");
        
        if (origin != "*") {
            res.add_header("Vary", "Origin");
        }
    }

    void after_handle(crow::request& req, crow::response& res, context& ctx) {
        // CORS headers already set in before_handle
    }

private:
    std::vector<std::string> allowed_origins_;
    bool allow_credentials_;
    std::string allowed_methods_;
    std::string allowed_headers_;

    static std::string join(const std::vector<std::string>& vec, const std::string& delim) {
        std::string result;
        for (size_t i = 0; i < vec.size(); ++i) {
            if (i > 0) result += delim;
            result += vec[i];
        }
        return result;
    }
};

} // namespace middleware
} // namespace prompt_portal

