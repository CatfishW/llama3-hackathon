#pragma once

#include <string>
#include <optional>
#include <chrono>
#include <nlohmann/json.hpp>

namespace prompt_portal {

// Enum types
enum class FriendshipStatus {
    PENDING,
    ACCEPTED,
    BLOCKED
};

inline std::string friendship_status_to_string(FriendshipStatus status) {
    switch (status) {
        case FriendshipStatus::PENDING: return "pending";
        case FriendshipStatus::ACCEPTED: return "accepted";
        case FriendshipStatus::BLOCKED: return "blocked";
    }
    return "pending";
}

inline FriendshipStatus string_to_friendship_status(const std::string& s) {
    if (s == "accepted") return FriendshipStatus::ACCEPTED;
    if (s == "blocked") return FriendshipStatus::BLOCKED;
    return FriendshipStatus::PENDING;
}

// Helper for datetime formatting
inline std::string current_timestamp() {
    auto now = std::chrono::system_clock::now();
    auto time = std::chrono::system_clock::to_time_t(now);
    char buf[32];
    std::strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", std::gmtime(&time));
    return std::string(buf);
}

// User model
struct User {
    int id = 0;
    std::string email;
    std::string password_hash;
    
    // Profile fields
    std::optional<std::string> full_name;
    std::optional<std::string> display_name;
    std::optional<std::string> school;
    std::optional<std::string> birthday;
    std::optional<std::string> bio;
    std::optional<std::string> status;
    std::optional<std::string> location;
    std::optional<std::string> website;
    std::optional<std::string> profile_picture;
    
    // Game stats
    int level = 1;
    int points = 0;
    int rank = 0;
    
    // Privacy settings
    bool profile_visible = true;
    bool allow_friend_requests = true;
    bool show_online_status = true;
    
    // Notification settings
    bool email_notifications = true;
    bool push_notifications = true;
    bool friend_request_notifications = true;
    bool message_notifications = true;
    
    // Security
    bool two_factor_enabled = false;
    std::string last_seen;
    bool is_online = false;
    
    // Model selection
    std::string selected_model = "TangLLM";
    
    std::string created_at;
    std::string updated_at;
    
    nlohmann::json to_json() const {
        nlohmann::json j;
        j["id"] = id;
        j["email"] = email;
        j["full_name"] = full_name.value_or("");
        j["display_name"] = display_name.value_or("");
        j["school"] = school.value_or("");
        j["birthday"] = birthday.value_or("");
        j["bio"] = bio.value_or("");
        j["status"] = status.value_or("");
        j["location"] = location.value_or("");
        j["website"] = website.value_or("");
        j["profile_picture"] = profile_picture.value_or("");
        j["level"] = level;
        j["points"] = points;
        j["rank"] = rank;
        j["is_online"] = is_online;
        j["last_seen"] = last_seen;
        j["created_at"] = created_at;
        return j;
    }
};

// Prompt Template model
struct PromptTemplate {
    int id = 0;
    int user_id = 0;
    std::string title;
    std::string description;
    std::string content;
    bool is_active = true;
    int version = 1;
    std::string created_at;
    std::string updated_at;
    
    nlohmann::json to_json() const {
        nlohmann::json j;
        j["id"] = id;
        j["user_id"] = user_id;
        j["title"] = title;
        j["description"] = description;
        j["content"] = content;
        j["is_active"] = is_active;
        j["version"] = version;
        j["created_at"] = created_at;
        j["updated_at"] = updated_at;
        return j;
    }
};

// Score model (Maze Game)
struct Score {
    int id = 0;
    int user_id = 0;
    int template_id = 0;
    std::string session_id;
    double score = 0.0;
    std::optional<double> new_score;
    double survival_time = 0.0;
    int oxygen_collected = 0;
    int germs = 0;
    std::string mode = "manual";
    
    // Comprehensive metrics
    std::optional<int> total_steps;
    std::optional<int> optimal_steps;
    std::optional<int> backtrack_count;
    std::optional<int> collision_count;
    std::optional<int> dead_end_entries;
    std::optional<double> avg_latency_ms;
    
    std::string created_at;
    
    nlohmann::json to_json() const {
        nlohmann::json j;
        j["id"] = id;
        j["user_id"] = user_id;
        j["template_id"] = template_id;
        j["session_id"] = session_id;
        j["score"] = score;
        j["new_score"] = new_score.value_or(0.0);
        j["survival_time"] = survival_time;
        j["oxygen_collected"] = oxygen_collected;
        j["germs"] = germs;
        j["mode"] = mode;
        j["total_steps"] = total_steps.value_or(0);
        j["optimal_steps"] = optimal_steps.value_or(0);
        j["backtrack_count"] = backtrack_count.value_or(0);
        j["collision_count"] = collision_count.value_or(0);
        j["dead_end_entries"] = dead_end_entries.value_or(0);
        j["avg_latency_ms"] = avg_latency_ms.value_or(0.0);
        j["created_at"] = created_at;
        return j;
    }
};

// Leaderboard entry
struct LeaderboardEntry {
    int rank = 0;
    std::string user_email;
    int template_id = 0;
    std::string template_title;
    double score = 0.0;
    std::optional<double> new_score;
    std::string session_id;
    std::string created_at;
    std::optional<int> total_steps;
    std::optional<int> collision_count;
    
    nlohmann::json to_json() const {
        nlohmann::json j;
        j["rank"] = rank;
        j["user_email"] = user_email;
        j["template_id"] = template_id;
        j["template_title"] = template_title;
        j["score"] = score;
        j["new_score"] = new_score.value_or(0.0);
        j["session_id"] = session_id;
        j["created_at"] = created_at;
        j["total_steps"] = total_steps.value_or(0);
        j["collision_count"] = collision_count.value_or(0);
        return j;
    }
};

// Announcement model
struct Announcement {
    int id = 0;
    std::string title;
    std::string content;
    std::string announcement_type = "info";
    int priority = 0;
    bool is_active = true;
    std::string created_by;
    std::string created_at;
    std::optional<std::string> expires_at;
    std::string updated_at;
    
    nlohmann::json to_json() const {
        nlohmann::json j;
        j["id"] = id;
        j["title"] = title;
        j["content"] = content;
        j["announcement_type"] = announcement_type;
        j["priority"] = priority;
        j["is_active"] = is_active;
        j["created_by"] = created_by;
        j["created_at"] = created_at;
        j["expires_at"] = expires_at.value_or("");
        j["updated_at"] = updated_at;
        return j;
    }
};

} // namespace prompt_portal

