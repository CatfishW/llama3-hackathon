#pragma once

#include <string>
#include <optional>
#include <chrono>
#include <nlohmann/json.hpp>

namespace prompt_portal {
namespace utils {

struct JwtPayload {
    int user_id;
    std::chrono::system_clock::time_point exp;
};

class JwtUtils {
public:
    static std::string encode(const nlohmann::json& payload, const std::string& secret);
    static std::optional<nlohmann::json> decode(const std::string& token, const std::string& secret);
    
    static std::string create_access_token(int user_id, const std::string& secret, int expire_minutes);
    static std::optional<JwtPayload> verify_token(const std::string& token, const std::string& secret);

private:
    static std::string base64_url_encode(const std::string& input);
    static std::string base64_url_decode(const std::string& input);
    static std::string hmac_sha256(const std::string& data, const std::string& key);
};

} // namespace utils
} // namespace prompt_portal

