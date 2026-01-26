#include "database.hpp"
#include <iostream>
#include <sstream>

namespace prompt_portal {

Database& Database::instance() {
    static Database instance;
    return instance;
}

void Database::initialize() {
    auto& config = get_config();
    db_ = std::make_unique<SQLite::Database>(
        config.database.path, 
        SQLite::OPEN_READWRITE | SQLite::OPEN_CREATE
    );
    create_tables();
    std::cout << "[Database] Initialized: " << config.database.path << std::endl;
}

void Database::create_tables() {
    // Users table
    db_->exec(R"(
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            display_name TEXT,
            school TEXT,
            birthday TEXT,
            bio TEXT,
            status TEXT,
            location TEXT,
            website TEXT,
            profile_picture TEXT,
            level INTEGER DEFAULT 1,
            points INTEGER DEFAULT 0,
            rank INTEGER DEFAULT 0,
            profile_visible INTEGER DEFAULT 1,
            allow_friend_requests INTEGER DEFAULT 1,
            show_online_status INTEGER DEFAULT 1,
            email_notifications INTEGER DEFAULT 1,
            push_notifications INTEGER DEFAULT 1,
            friend_request_notifications INTEGER DEFAULT 1,
            message_notifications INTEGER DEFAULT 1,
            two_factor_enabled INTEGER DEFAULT 0,
            last_seen TEXT,
            is_online INTEGER DEFAULT 0,
            selected_model TEXT DEFAULT 'TangLLM',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    )");

    // Prompt templates table
    db_->exec(R"(
        CREATE TABLE IF NOT EXISTS prompt_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            content TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            version INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    )");

    // Scores table (Maze Game)
    db_->exec(R"(
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            template_id INTEGER NOT NULL,
            session_id TEXT NOT NULL,
            score REAL DEFAULT 0.0,
            new_score REAL,
            survival_time REAL DEFAULT 0.0,
            oxygen_collected INTEGER DEFAULT 0,
            germs INTEGER DEFAULT 0,
            mode TEXT DEFAULT 'manual',
            total_steps INTEGER,
            optimal_steps INTEGER,
            backtrack_count INTEGER,
            collision_count INTEGER,
            dead_end_entries INTEGER,
            avg_latency_ms REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (template_id) REFERENCES prompt_templates(id)
        )
    )");

    // Announcements table
    db_->exec(R"(
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            announcement_type TEXT DEFAULT 'info',
            priority INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_by TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    )");

    // Create indexes
    db_->exec("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)");
    db_->exec("CREATE INDEX IF NOT EXISTS idx_templates_user ON prompt_templates(user_id)");
    db_->exec("CREATE INDEX IF NOT EXISTS idx_scores_user ON scores(user_id)");
    db_->exec("CREATE INDEX IF NOT EXISTS idx_scores_template ON scores(template_id)");
}

User Database::row_to_user(SQLite::Statement& query) {
    User user;
    user.id = query.getColumn("id").getInt();
    user.email = query.getColumn("email").getText();
    user.password_hash = query.getColumn("password_hash").getText();
    
    if (!query.getColumn("full_name").isNull())
        user.full_name = query.getColumn("full_name").getText();
    if (!query.getColumn("display_name").isNull())
        user.display_name = query.getColumn("display_name").getText();
    if (!query.getColumn("school").isNull())
        user.school = query.getColumn("school").getText();
    if (!query.getColumn("birthday").isNull())
        user.birthday = query.getColumn("birthday").getText();
    if (!query.getColumn("bio").isNull())
        user.bio = query.getColumn("bio").getText();
    if (!query.getColumn("status").isNull())
        user.status = query.getColumn("status").getText();
    if (!query.getColumn("location").isNull())
        user.location = query.getColumn("location").getText();
    if (!query.getColumn("website").isNull())
        user.website = query.getColumn("website").getText();
    if (!query.getColumn("profile_picture").isNull())
        user.profile_picture = query.getColumn("profile_picture").getText();
    
    user.level = query.getColumn("level").getInt();
    user.points = query.getColumn("points").getInt();
    user.rank = query.getColumn("rank").getInt();
    user.profile_visible = query.getColumn("profile_visible").getInt() != 0;
    user.allow_friend_requests = query.getColumn("allow_friend_requests").getInt() != 0;
    user.show_online_status = query.getColumn("show_online_status").getInt() != 0;
    user.is_online = query.getColumn("is_online").getInt() != 0;
    
    if (!query.getColumn("last_seen").isNull())
        user.last_seen = query.getColumn("last_seen").getText();
    if (!query.getColumn("created_at").isNull())
        user.created_at = query.getColumn("created_at").getText();
    if (!query.getColumn("updated_at").isNull())
        user.updated_at = query.getColumn("updated_at").getText();
    
    return user;
}

std::optional<User> Database::find_user_by_email(const std::string& email) {
    SQLite::Statement query(*db_, "SELECT * FROM users WHERE email = ?");
    query.bind(1, email);
    
    if (query.executeStep()) {
        return row_to_user(query);
    }
    return std::nullopt;
}

std::optional<User> Database::find_user_by_id(int id) {
    SQLite::Statement query(*db_, "SELECT * FROM users WHERE id = ?");
    query.bind(1, id);
    
    if (query.executeStep()) {
        return row_to_user(query);
    }
    return std::nullopt;
}

User Database::create_user(const std::string& email, const std::string& password_hash) {
    SQLite::Statement insert(*db_, 
        "INSERT INTO users (email, password_hash, last_seen) VALUES (?, ?, datetime('now'))");
    insert.bind(1, email);
    insert.bind(2, password_hash);
    insert.exec();
    
    int id = static_cast<int>(db_->getLastInsertRowid());
    return *find_user_by_id(id);
}

bool Database::update_user(const User& user) {
    SQLite::Statement update(*db_, R"(
        UPDATE users SET 
            full_name = ?, display_name = ?, school = ?, birthday = ?, bio = ?,
            status = ?, location = ?, website = ?, profile_picture = ?,
            level = ?, points = ?, rank = ?, is_online = ?,
            updated_at = datetime('now')
        WHERE id = ?
    )");
    
    update.bind(1, user.full_name.value_or(""));
    update.bind(2, user.display_name.value_or(""));
    update.bind(3, user.school.value_or(""));
    update.bind(4, user.birthday.value_or(""));
    update.bind(5, user.bio.value_or(""));
    update.bind(6, user.status.value_or(""));
    update.bind(7, user.location.value_or(""));
    update.bind(8, user.website.value_or(""));
    update.bind(9, user.profile_picture.value_or(""));
    update.bind(10, user.level);
    update.bind(11, user.points);
    update.bind(12, user.rank);
    update.bind(13, user.is_online ? 1 : 0);
    update.bind(14, user.id);
    
    return update.exec() > 0;
}

bool Database::delete_user(int id) {
    SQLite::Statement del(*db_, "DELETE FROM users WHERE id = ?");
    del.bind(1, id);
    return del.exec() > 0;
}

std::vector<User> Database::search_users(const std::string& query_str, int limit) {
    std::vector<User> users;
    std::string search = "%" + query_str + "%";
    
    SQLite::Statement query(*db_, 
        "SELECT * FROM users WHERE email LIKE ? OR full_name LIKE ? LIMIT ?");
    query.bind(1, search);
    query.bind(2, search);
    query.bind(3, limit);
    
    while (query.executeStep()) {
        users.push_back(row_to_user(query));
    }
    return users;
}

int Database::count_users() {
    SQLite::Statement query(*db_, "SELECT COUNT(*) FROM users");
    query.executeStep();
    return query.getColumn(0).getInt();
}

PromptTemplate Database::row_to_template(SQLite::Statement& query) {
    PromptTemplate tmpl;
    tmpl.id = query.getColumn("id").getInt();
    tmpl.user_id = query.getColumn("user_id").getInt();
    tmpl.title = query.getColumn("title").getText();
    tmpl.description = query.getColumn("description").getText();
    tmpl.content = query.getColumn("content").getText();
    tmpl.is_active = query.getColumn("is_active").getInt() != 0;
    tmpl.version = query.getColumn("version").getInt();
    tmpl.created_at = query.getColumn("created_at").getText();
    tmpl.updated_at = query.getColumn("updated_at").getText();
    return tmpl;
}

PromptTemplate Database::create_template(int user_id, const std::string& title,
                                          const std::string& description,
                                          const std::string& content,
                                          bool is_active, int version) {
    SQLite::Statement insert(*db_, R"(
        INSERT INTO prompt_templates (user_id, title, description, content, is_active, version)
        VALUES (?, ?, ?, ?, ?, ?)
    )");
    insert.bind(1, user_id);
    insert.bind(2, title);
    insert.bind(3, description);
    insert.bind(4, content);
    insert.bind(5, is_active ? 1 : 0);
    insert.bind(6, version);
    insert.exec();
    
    int id = static_cast<int>(db_->getLastInsertRowid());
    return *find_template_by_id(id);
}

std::optional<PromptTemplate> Database::find_template_by_id(int id) {
    SQLite::Statement query(*db_, "SELECT * FROM prompt_templates WHERE id = ?");
    query.bind(1, id);
    
    if (query.executeStep()) {
        return row_to_template(query);
    }
    return std::nullopt;
}

std::vector<PromptTemplate> Database::list_templates(int user_id, int skip, int limit, bool mine) {
    std::vector<PromptTemplate> templates;
    
    std::string sql = "SELECT * FROM prompt_templates";
    if (mine) {
        sql += " WHERE user_id = ?";
    }
    sql += " ORDER BY updated_at DESC LIMIT ? OFFSET ?";
    
    SQLite::Statement query(*db_, sql);
    int idx = 1;
    if (mine) {
        query.bind(idx++, user_id);
    }
    query.bind(idx++, limit);
    query.bind(idx, skip);
    
    while (query.executeStep()) {
        templates.push_back(row_to_template(query));
    }
    return templates;
}

bool Database::update_template(const PromptTemplate& tmpl) {
    SQLite::Statement update(*db_, R"(
        UPDATE prompt_templates SET 
            title = ?, description = ?, content = ?, is_active = ?, version = ?,
            updated_at = datetime('now')
        WHERE id = ?
    )");
    update.bind(1, tmpl.title);
    update.bind(2, tmpl.description);
    update.bind(3, tmpl.content);
    update.bind(4, tmpl.is_active ? 1 : 0);
    update.bind(5, tmpl.version);
    update.bind(6, tmpl.id);
    
    return update.exec() > 0;
}

bool Database::delete_template(int id) {
    // Delete associated scores first
    SQLite::Statement del_scores(*db_, "DELETE FROM scores WHERE template_id = ?");
    del_scores.bind(1, id);
    del_scores.exec();
    
    SQLite::Statement del(*db_, "DELETE FROM prompt_templates WHERE id = ?");
    del.bind(1, id);
    return del.exec() > 0;
}

Score Database::row_to_score(SQLite::Statement& query) {
    Score score;
    score.id = query.getColumn("id").getInt();
    score.user_id = query.getColumn("user_id").getInt();
    score.template_id = query.getColumn("template_id").getInt();
    score.session_id = query.getColumn("session_id").getText();
    score.score = query.getColumn("score").getDouble();
    
    if (!query.getColumn("new_score").isNull())
        score.new_score = query.getColumn("new_score").getDouble();
    
    score.survival_time = query.getColumn("survival_time").getDouble();
    score.oxygen_collected = query.getColumn("oxygen_collected").getInt();
    score.germs = query.getColumn("germs").getInt();
    score.mode = query.getColumn("mode").getText();
    
    if (!query.getColumn("total_steps").isNull())
        score.total_steps = query.getColumn("total_steps").getInt();
    if (!query.getColumn("collision_count").isNull())
        score.collision_count = query.getColumn("collision_count").getInt();
    
    score.created_at = query.getColumn("created_at").getText();
    return score;
}

Score Database::create_score(const Score& s) {
    SQLite::Statement insert(*db_, R"(
        INSERT INTO scores (user_id, template_id, session_id, score, new_score,
            survival_time, oxygen_collected, germs, mode, total_steps, optimal_steps,
            backtrack_count, collision_count, dead_end_entries, avg_latency_ms)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    )");
    
    insert.bind(1, s.user_id);
    insert.bind(2, s.template_id);
    insert.bind(3, s.session_id);
    insert.bind(4, s.score);
    
    if (s.new_score) insert.bind(5, *s.new_score);
    else insert.bind(5);
    
    insert.bind(6, s.survival_time);
    insert.bind(7, s.oxygen_collected);
    insert.bind(8, s.germs);
    insert.bind(9, s.mode);
    
    if (s.total_steps) insert.bind(10, *s.total_steps);
    else insert.bind(10);
    if (s.optimal_steps) insert.bind(11, *s.optimal_steps);
    else insert.bind(11);
    if (s.backtrack_count) insert.bind(12, *s.backtrack_count);
    else insert.bind(12);
    if (s.collision_count) insert.bind(13, *s.collision_count);
    else insert.bind(13);
    if (s.dead_end_entries) insert.bind(14, *s.dead_end_entries);
    else insert.bind(14);
    if (s.avg_latency_ms) insert.bind(15, *s.avg_latency_ms);
    else insert.bind(15);
    
    insert.exec();
    
    Score result = s;
    result.id = static_cast<int>(db_->getLastInsertRowid());
    result.created_at = current_timestamp();
    return result;
}

std::vector<LeaderboardEntry> Database::get_leaderboard(int limit, int skip, const std::string& mode) {
    std::vector<LeaderboardEntry> entries;
    
    std::string sql = R"(
        SELECT s.*, u.email, t.title as template_title
        FROM scores s
        JOIN users u ON s.user_id = u.id
        JOIN prompt_templates t ON s.template_id = t.id
    )";
    
    if (mode == "lam" || mode == "manual") {
        sql += " WHERE s.mode = ?";
    }
    
    sql += " ORDER BY COALESCE(s.new_score, 0) DESC, s.score DESC, s.created_at ASC LIMIT ? OFFSET ?";
    
    SQLite::Statement query(*db_, sql);
    int idx = 1;
    if (mode == "lam" || mode == "manual") {
        query.bind(idx++, mode);
    }
    query.bind(idx++, limit);
    query.bind(idx, skip);
    
    int rank = skip + 1;
    while (query.executeStep()) {
        LeaderboardEntry entry;
        entry.rank = rank++;
        entry.user_email = query.getColumn("email").getText();
        entry.template_id = query.getColumn("template_id").getInt();
        entry.template_title = query.getColumn("template_title").getText();
        entry.score = query.getColumn("score").getDouble();
        
        if (!query.getColumn("new_score").isNull())
            entry.new_score = query.getColumn("new_score").getDouble();
        
        entry.session_id = query.getColumn("session_id").getText();
        entry.created_at = query.getColumn("created_at").getText();
        
        if (!query.getColumn("total_steps").isNull())
            entry.total_steps = query.getColumn("total_steps").getInt();
        if (!query.getColumn("collision_count").isNull())
            entry.collision_count = query.getColumn("collision_count").getInt();
        
        entries.push_back(entry);
    }
    return entries;
}

int Database::count_scores() {
    SQLite::Statement query(*db_, "SELECT COUNT(*) FROM scores");
    query.executeStep();
    return query.getColumn(0).getInt();
}

int Database::count_participants() {
    SQLite::Statement query(*db_, "SELECT COUNT(DISTINCT user_id) FROM scores");
    query.executeStep();
    return query.getColumn(0).getInt();
}

Announcement Database::row_to_announcement(SQLite::Statement& query) {
    Announcement ann;
    ann.id = query.getColumn("id").getInt();
    ann.title = query.getColumn("title").getText();
    ann.content = query.getColumn("content").getText();
    ann.announcement_type = query.getColumn("announcement_type").getText();
    ann.priority = query.getColumn("priority").getInt();
    ann.is_active = query.getColumn("is_active").getInt() != 0;
    ann.created_by = query.getColumn("created_by").getText();
    ann.created_at = query.getColumn("created_at").getText();
    
    if (!query.getColumn("expires_at").isNull())
        ann.expires_at = query.getColumn("expires_at").getText();
    
    ann.updated_at = query.getColumn("updated_at").getText();
    return ann;
}

Announcement Database::create_announcement(const Announcement& a) {
    SQLite::Statement insert(*db_, R"(
        INSERT INTO announcements (title, content, announcement_type, priority, is_active, created_by, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    )");
    
    insert.bind(1, a.title);
    insert.bind(2, a.content);
    insert.bind(3, a.announcement_type);
    insert.bind(4, a.priority);
    insert.bind(5, a.is_active ? 1 : 0);
    insert.bind(6, a.created_by);
    
    if (a.expires_at) insert.bind(7, *a.expires_at);
    else insert.bind(7);
    
    insert.exec();
    
    Announcement result = a;
    result.id = static_cast<int>(db_->getLastInsertRowid());
    result.created_at = current_timestamp();
    result.updated_at = result.created_at;
    return result;
}

std::vector<Announcement> Database::list_announcements(bool active_only, int limit) {
    std::vector<Announcement> announcements;
    
    std::string sql = "SELECT * FROM announcements";
    if (active_only) {
        sql += " WHERE is_active = 1";
    }
    sql += " ORDER BY priority DESC, created_at DESC LIMIT ?";
    
    SQLite::Statement query(*db_, sql);
    query.bind(1, limit);
    
    while (query.executeStep()) {
        announcements.push_back(row_to_announcement(query));
    }
    return announcements;
}

bool Database::update_announcement(const Announcement& a) {
    SQLite::Statement update(*db_, R"(
        UPDATE announcements SET 
            title = ?, content = ?, announcement_type = ?, priority = ?,
            is_active = ?, expires_at = ?, updated_at = datetime('now')
        WHERE id = ?
    )");
    
    update.bind(1, a.title);
    update.bind(2, a.content);
    update.bind(3, a.announcement_type);
    update.bind(4, a.priority);
    update.bind(5, a.is_active ? 1 : 0);
    
    if (a.expires_at) update.bind(6, *a.expires_at);
    else update.bind(6);
    
    update.bind(7, a.id);
    
    return update.exec() > 0;
}

bool Database::delete_announcement(int id) {
    SQLite::Statement del(*db_, "DELETE FROM announcements WHERE id = ?");
    del.bind(1, id);
    return del.exec() > 0;
}

} // namespace prompt_portal

