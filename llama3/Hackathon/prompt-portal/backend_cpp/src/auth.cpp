#include "auth.hpp"
#include "database.hpp"
#include "config.hpp"
#include "utils/password.hpp"
#include "utils/jwt_utils.hpp"
#include <algorithm>

namespace prompt_portal {

Auth& Auth::instance() {
    static Auth instance;
    return instance;
}

std::string Auth::hash_password(const std::string& password) {
    return utils::PasswordHasher::hash(password);
}

bool Auth::verify_password(const std::string& password, const std::string& hash) {
    return utils::PasswordHasher::verify(password, hash);
}

std::string Auth::create_access_token(int user_id, int expires_minutes) {
    auto& config = get_config();
    int exp = expires_minutes > 0 ? expires_minutes : config.auth.token_expire_minutes;
    return utils::JwtUtils::create_access_token(user_id, config.auth.secret_key, exp);
}

std::optional<TokenPayload> Auth::decode_token(const std::string& token) {
    auto& config = get_config();
    auto payload = utils::JwtUtils::verify_token(token, config.auth.secret_key);
    
    if (!payload) {
        return std::nullopt;
    }
    
    TokenPayload result;
    result.user_id = payload->user_id;
    return result;
}

std::string Auth::extract_token(const std::string& auth_header) {
    // Format: "Bearer <token>"
    const std::string prefix = "Bearer ";
    if (auth_header.substr(0, prefix.length()) == prefix) {
        return auth_header.substr(prefix.length());
    }
    return auth_header;
}

std::optional<User> Auth::get_current_user(const std::string& auth_header) {
    if (auth_header.empty()) {
        return std::nullopt;
    }
    
    std::string token = extract_token(auth_header);
    auto payload = decode_token(token);
    
    if (!payload) {
        return std::nullopt;
    }
    
    return Database::instance().find_user_by_id(payload->user_id);
}

} // namespace prompt_portal

