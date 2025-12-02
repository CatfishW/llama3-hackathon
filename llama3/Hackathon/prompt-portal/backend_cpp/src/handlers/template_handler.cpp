#include "handlers/template_handler.hpp"
#include "database.hpp"
#include "auth.hpp"
#include <iostream>

namespace prompt_portal {
namespace handlers {

crow::response TemplateHandler::error_response(int status, const std::string& detail) {
    nlohmann::json error = {{"detail", detail}};
    crow::response res(status, error.dump());
    res.set_header("Content-Type", "application/json");
    return res;
}

crow::response TemplateHandler::json_response(int status, const nlohmann::json& data) {
    crow::response res(status, data.dump());
    res.set_header("Content-Type", "application/json");
    return res;
}

crow::response TemplateHandler::create(const crow::request& req) {
    try {
        std::string auth_header = req.get_header_value("Authorization");
        auto user = Auth::instance().get_current_user(auth_header);
        
        if (!user) {
            return error_response(401, "Could not validate credentials");
        }
        
        auto body = nlohmann::json::parse(req.body);
        
        std::string title = body.value("title", "");
        std::string description = body.value("description", "");
        std::string content = body.value("content", "");
        bool is_active = body.value("is_active", true);
        int version = body.value("version", 1);
        
        if (title.empty() || content.empty()) {
            return error_response(400, "Title and content are required");
        }
        
        auto tmpl = Database::instance().create_template(
            user->id, title, description, content, is_active, version
        );
        
        std::cout << "[Templates] Created template: " << title << " (ID: " << tmpl.id << ")" << std::endl;
        return json_response(201, tmpl.to_json());
        
    } catch (const std::exception& e) {
        std::cerr << "[Templates] Create error: " << e.what() << std::endl;
        return error_response(500, "Internal server error");
    }
}

crow::response TemplateHandler::list(const crow::request& req) {
    try {
        std::string auth_header = req.get_header_value("Authorization");
        auto user = Auth::instance().get_current_user(auth_header);
        
        if (!user) {
            return error_response(401, "Could not validate credentials");
        }
        
        // Parse query parameters
        int skip = 0;
        int limit = 50;
        bool mine = true;
        
        auto skip_param = req.url_params.get("skip");
        auto limit_param = req.url_params.get("limit");
        auto mine_param = req.url_params.get("mine");
        
        if (skip_param) skip = std::stoi(skip_param);
        if (limit_param) limit = std::stoi(limit_param);
        if (mine_param) mine = std::string(mine_param) == "true";
        
        auto templates = Database::instance().list_templates(user->id, skip, limit, mine);
        
        nlohmann::json result = nlohmann::json::array();
        for (const auto& tmpl : templates) {
            result.push_back(tmpl.to_json());
        }
        
        return json_response(200, result);
        
    } catch (const std::exception& e) {
        std::cerr << "[Templates] List error: " << e.what() << std::endl;
        return error_response(500, "Internal server error");
    }
}

crow::response TemplateHandler::get(const crow::request& req, int id) {
    try {
        std::string auth_header = req.get_header_value("Authorization");
        auto user = Auth::instance().get_current_user(auth_header);
        
        if (!user) {
            return error_response(401, "Could not validate credentials");
        }
        
        auto tmpl = Database::instance().find_template_by_id(id);
        
        if (!tmpl || tmpl->user_id != user->id) {
            return error_response(404, "Template not found");
        }
        
        return json_response(200, tmpl->to_json());
        
    } catch (const std::exception& e) {
        std::cerr << "[Templates] Get error: " << e.what() << std::endl;
        return error_response(500, "Internal server error");
    }
}

crow::response TemplateHandler::get_public(int id) {
    try {
        auto tmpl = Database::instance().find_template_by_id(id);
        
        if (!tmpl) {
            return error_response(404, "Template not found");
        }
        
        return json_response(200, tmpl->to_json());
        
    } catch (const std::exception& e) {
        std::cerr << "[Templates] Get public error: " << e.what() << std::endl;
        return error_response(500, "Internal server error");
    }
}

crow::response TemplateHandler::update(const crow::request& req, int id) {
    try {
        std::string auth_header = req.get_header_value("Authorization");
        auto user = Auth::instance().get_current_user(auth_header);
        
        if (!user) {
            return error_response(401, "Could not validate credentials");
        }
        
        auto tmpl = Database::instance().find_template_by_id(id);
        
        if (!tmpl || tmpl->user_id != user->id) {
            return error_response(404, "Template not found");
        }
        
        auto body = nlohmann::json::parse(req.body);
        
        if (body.contains("title")) tmpl->title = body["title"];
        if (body.contains("description")) tmpl->description = body["description"];
        if (body.contains("content")) tmpl->content = body["content"];
        if (body.contains("is_active")) tmpl->is_active = body["is_active"];
        if (body.contains("version")) tmpl->version = body["version"];
        
        Database::instance().update_template(*tmpl);
        
        std::cout << "[Templates] Updated template ID: " << id << std::endl;
        return json_response(200, tmpl->to_json());
        
    } catch (const std::exception& e) {
        std::cerr << "[Templates] Update error: " << e.what() << std::endl;
        return error_response(500, "Internal server error");
    }
}

crow::response TemplateHandler::remove(const crow::request& req, int id) {
    try {
        std::string auth_header = req.get_header_value("Authorization");
        auto user = Auth::instance().get_current_user(auth_header);
        
        if (!user) {
            return error_response(401, "Could not validate credentials");
        }
        
        auto tmpl = Database::instance().find_template_by_id(id);
        
        if (!tmpl || tmpl->user_id != user->id) {
            return error_response(404, "Template not found");
        }
        
        Database::instance().delete_template(id);
        
        std::cout << "[Templates] Deleted template ID: " << id << std::endl;
        return json_response(200, {{"ok", true}});
        
    } catch (const std::exception& e) {
        std::cerr << "[Templates] Delete error: " << e.what() << std::endl;
        return error_response(500, "Internal server error");
    }
}

} // namespace handlers
} // namespace prompt_portal

