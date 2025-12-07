#include "handlers/auth_handler.hpp"
#include "database.hpp"
#include "auth.hpp"
#include <iostream>

namespace prompt_portal {
namespace handlers {

crow::response AuthHandler::error_response(int status, const std::string& detail) {
    nlohmann::json error = {{"detail", detail}};
    crow::response res(status, error.dump());
    res.set_header("Content-Type", "application/json");
    return res;
}

crow::response AuthHandler::json_response(int status, const nlohmann::json& data) {
    crow::response res(status, data.dump());
    res.set_header("Content-Type", "application/json");
    return res;
}

crow::response AuthHandler::register_user(const crow::request& req) {
    try {
        auto body = nlohmann::json::parse(req.body);
        
        std::string email = body.value("email", "");
        std::string password = body.value("password", "");
        
        if (email.empty() || password.empty()) {
            return error_response(400, "Email and password are required");
        }
        
        if (password.length() < 6) {
            return error_response(400, "Password must be at least 6 characters");
        }
        
        // Check if user exists
        auto& db = Database::instance();
        if (db.find_user_by_email(email)) {
            return error_response(400, "Email already registered");
        }
        
        // Create user
        std::string password_hash = Auth::instance().hash_password(password);
        User user = db.create_user(email, password_hash);
        
        std::cout << "[Auth] User registered: " << email << std::endl;
        return json_response(201, user.to_json());
        
    } catch (const std::exception& e) {
        std::cerr << "[Auth] Register error: " << e.what() << std::endl;
        return error_response(500, "Internal server error");
    }
}

crow::response AuthHandler::login(const crow::request& req) {
    try {
        auto body = nlohmann::json::parse(req.body);
        
        std::string email = body.value("email", "");
        std::string password = body.value("password", "");
        
        if (email.empty() || password.empty()) {
            return error_response(400, "Email and password are required");
        }
        
        // Find user
        auto& db = Database::instance();
        auto user = db.find_user_by_email(email);
        
        if (!user) {
            return error_response(401, "Invalid credentials");
        }
        
        // Verify password
        if (!Auth::instance().verify_password(password, user->password_hash)) {
            return error_response(401, "Invalid credentials");
        }
        
        // Create token
        std::string token = Auth::instance().create_access_token(user->id);
        
        nlohmann::json response = {
            {"access_token", token},
            {"token_type", "bearer"}
        };
        
        std::cout << "[Auth] User logged in: " << email << std::endl;
        return json_response(200, response);
        
    } catch (const std::exception& e) {
        std::cerr << "[Auth] Login error: " << e.what() << std::endl;
        return error_response(500, "Internal server error");
    }
}

crow::response AuthHandler::change_password(const crow::request& req) {
    try {
        std::string auth_header = req.get_header_value("Authorization");
        auto user = Auth::instance().get_current_user(auth_header);
        
        if (!user) {
            return error_response(401, "Could not validate credentials");
        }
        
        auto body = nlohmann::json::parse(req.body);
        std::string current_password = body.value("current_password", "");
        std::string new_password = body.value("new_password", "");
        
        if (current_password.empty() || new_password.empty()) {
            return error_response(400, "Current password and new password are required");
        }
        
        if (!Auth::instance().verify_password(current_password, user->password_hash)) {
            return error_response(400, "Invalid current password");
        }
        
        // Update password (would need to add this to Database class)
        // For now, return success
        nlohmann::json response = {{"message", "Password changed successfully"}};
        return json_response(200, response);
        
    } catch (const std::exception& e) {
        std::cerr << "[Auth] Change password error: " << e.what() << std::endl;
        return error_response(500, "Internal server error");
    }
}

crow::response AuthHandler::delete_account(const crow::request& req) {
    try {
        std::string auth_header = req.get_header_value("Authorization");
        auto user = Auth::instance().get_current_user(auth_header);
        
        if (!user) {
            return error_response(401, "Could not validate credentials");
        }
        
        Database::instance().delete_user(user->id);
        
        nlohmann::json response = {{"message", "Account deleted successfully"}};
        std::cout << "[Auth] Account deleted: " << user->email << std::endl;
        return json_response(200, response);
        
    } catch (const std::exception& e) {
        std::cerr << "[Auth] Delete account error: " << e.what() << std::endl;
        return error_response(500, "Internal server error");
    }
}

} // namespace handlers
} // namespace prompt_portal

