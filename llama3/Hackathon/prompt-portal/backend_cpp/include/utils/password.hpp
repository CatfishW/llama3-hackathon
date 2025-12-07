#pragma once

#include <string>

namespace prompt_portal {
namespace utils {

/**
 * Simple password hashing using SHA-256 + salt
 * For production, use bcrypt or argon2
 */
class PasswordHasher {
public:
    static std::string hash(const std::string& password);
    static bool verify(const std::string& password, const std::string& hash);
    
private:
    static std::string generate_salt(size_t length = 16);
    static std::string sha256(const std::string& input);
};

} // namespace utils
} // namespace prompt_portal

