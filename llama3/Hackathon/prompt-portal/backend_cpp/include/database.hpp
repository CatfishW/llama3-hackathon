#pragma once

#include <string>
#include <memory>
#include <optional>
#include <vector>
#include <SQLiteCpp/SQLiteCpp.h>
#include "models.hpp"
#include "config.hpp"

namespace prompt_portal {

class Database {
public:
    static Database& instance();
    
    void initialize();
    
    // User operations
    std::optional<User> find_user_by_email(const std::string& email);
    std::optional<User> find_user_by_id(int id);
    User create_user(const std::string& email, const std::string& password_hash);
    bool update_user(const User& user);
    bool delete_user(int id);
    std::vector<User> search_users(const std::string& query, int limit = 20);
    int count_users();
    
    // Template operations
    PromptTemplate create_template(int user_id, const std::string& title, 
                                   const std::string& description, 
                                   const std::string& content,
                                   bool is_active = true, int version = 1);
    std::optional<PromptTemplate> find_template_by_id(int id);
    std::vector<PromptTemplate> list_templates(int user_id, int skip = 0, int limit = 50, bool mine = true);
    bool update_template(const PromptTemplate& tmpl);
    bool delete_template(int id);
    
    // Score operations (Maze Game)
    Score create_score(const Score& score);
    std::vector<LeaderboardEntry> get_leaderboard(int limit = 20, int skip = 0, 
                                                   const std::string& mode = "");
    int count_scores();
    int count_participants();
    
    // Driving Game Score operations
    DrivingGameScore create_driving_score(const DrivingGameScore& score);
    std::vector<DrivingGameLeaderboardEntry> get_driving_leaderboard(int limit = 20, int skip = 0);
    int count_driving_scores();
    
    // Announcement operations
    Announcement create_announcement(const Announcement& announcement);
    std::vector<Announcement> list_announcements(bool active_only = true, int limit = 20);
    bool update_announcement(const Announcement& announcement);
    bool delete_announcement(int id);

private:
    Database() = default;
    ~Database() = default;
    Database(const Database&) = delete;
    Database& operator=(const Database&) = delete;
    
    std::unique_ptr<SQLite::Database> db_;
    
    void create_tables();
    User row_to_user(SQLite::Statement& query);
    PromptTemplate row_to_template(SQLite::Statement& query);
    Score row_to_score(SQLite::Statement& query);
    DrivingGameScore row_to_driving_score(SQLite::Statement& query);
    Announcement row_to_announcement(SQLite::Statement& query);
};

} // namespace prompt_portal

