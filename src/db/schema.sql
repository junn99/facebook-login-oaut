-- Instagram OAuth System Database Schema
-- SQLite database for storing user accounts, tokens, insights, and audience data

-- ============================================================
-- 1. USERS TABLE
-- Stores Instagram Business Account information
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instagram_account_id TEXT UNIQUE NOT NULL,  -- IG Business Account ID
    instagram_username TEXT,
    facebook_page_id TEXT,                      -- Facebook Page ID
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_instagram_account_id ON users(instagram_account_id);
CREATE INDEX IF NOT EXISTS idx_users_facebook_page_id ON users(facebook_page_id);

-- ============================================================
-- 2. TOKENS TABLE
-- Stores access tokens for API authentication
-- ============================================================
CREATE TABLE IF NOT EXISTS tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    user_access_token TEXT NOT NULL,            -- For refresh operations, expires ~60 days
    page_access_token TEXT NOT NULL,            -- For API calls, never expires while user token valid
    user_token_expires_at DATETIME NOT NULL,
    is_valid BOOLEAN DEFAULT 1,
    invalid_reason TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tokens_user_id ON tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_tokens_is_valid ON tokens(is_valid);
CREATE INDEX IF NOT EXISTS idx_tokens_expires_at ON tokens(user_token_expires_at);

-- ============================================================
-- 3. INSIGHTS TABLE
-- Stores Instagram metrics (impressions, reach, engagement, followers)
-- ============================================================
CREATE TABLE IF NOT EXISTS insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    metric_name TEXT NOT NULL,                  -- impressions, reach, accounts_engaged, follower_count
    metric_value INTEGER,
    period TEXT,                                -- day, lifetime
    collected_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_insights_user_id ON insights(user_id);
CREATE INDEX IF NOT EXISTS idx_insights_collected_at ON insights(collected_at);
CREATE INDEX IF NOT EXISTS idx_insights_metric_name ON insights(metric_name);
CREATE INDEX IF NOT EXISTS idx_insights_user_metric ON insights(user_id, metric_name, collected_at);

-- ============================================================
-- 4. AUDIENCE_DATA TABLE
-- Stores demographic insights (city, country, gender/age)
-- ============================================================
CREATE TABLE IF NOT EXISTS audience_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    metric_name TEXT NOT NULL,                  -- audience_city, audience_country, audience_gender_age
    metric_value TEXT,                          -- JSON string
    collected_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_audience_user_id ON audience_data(user_id);
CREATE INDEX IF NOT EXISTS idx_audience_collected_at ON audience_data(collected_at);
CREATE INDEX IF NOT EXISTS idx_audience_metric_name ON audience_data(metric_name);

-- ============================================================
-- 5. COLLECTION_LOG TABLE
-- Tracks API collection operations for monitoring and debugging
-- ============================================================
CREATE TABLE IF NOT EXISTS collection_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    collection_type TEXT NOT NULL,              -- insights, audience
    status TEXT NOT NULL,                       -- success, failed, rate_limited
    error_message TEXT,
    requests_made INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_collection_log_user_id ON collection_log(user_id);
CREATE INDEX IF NOT EXISTS idx_collection_log_created_at ON collection_log(created_at);
CREATE INDEX IF NOT EXISTS idx_collection_log_status ON collection_log(status);
