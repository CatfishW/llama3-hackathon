#pragma once

#include <string>
#include <optional>
#include "models.hpp"

namespace prompt_portal {

struct TokenPayload {
    int user_id;
    std::string exp;
};

class Auth {
public:
    static Auth& instance();
    
    // Password operations
    std::string hash_password(const std::string& password);
    bool verify_password(const std::string& password, const std::string& hash);
    
    // JWT operations
    std::string create_access_token(int user_id, int expires_minutes = 0);
    std::optional<TokenPayload> decode_token(const std::string& token);
    
    // Authentication
    std::optional<User> get_current_user(const std::string& auth_header);
    std::string extract_token(const std::string& auth_header);

private:
    Auth() = default;
    ~Auth() = default;
    Auth(const Auth&) = delete;
    Auth& operator=(const Auth&) = delete;
};

} // namespace prompt_portal

