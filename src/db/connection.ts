import Database from 'better-sqlite3';
import { readFileSync, existsSync, mkdirSync } from 'fs';
import { dirname, join } from 'path';
import { config } from '../config';

// Ensure data directory exists
const dataDir = dirname(config.databasePath);
if (!existsSync(dataDir)) {
  mkdirSync(dataDir, { recursive: true });
}

// Initialize database connection
const db = new Database(config.databasePath);
db.pragma('journal_mode = WAL'); // Better concurrent performance
db.pragma('foreign_keys = ON');  // Enforce foreign key constraints

// Initialize schema on first run
const schemaPath = join(__dirname, 'schema.sql');
const schema = readFileSync(schemaPath, 'utf-8');
db.exec(schema);

// ============================================================
// USER OPERATIONS
// ============================================================

export interface User {
  id: number;
  instagram_account_id: string;
  instagram_username: string | null;
  facebook_page_id: string | null;
  created_at: string;
  updated_at: string;
}

export function getUser(instagramAccountId: string): User | undefined {
  const stmt = db.prepare('SELECT * FROM users WHERE instagram_account_id = ?');
  return stmt.get(instagramAccountId) as User | undefined;
}

export function createUser(
  instagramAccountId: string,
  instagramUsername: string | null,
  facebookPageId: string | null
): User {
  const stmt = db.prepare(`
    INSERT INTO users (instagram_account_id, instagram_username, facebook_page_id)
    VALUES (?, ?, ?)
  `);
  const result = stmt.run(instagramAccountId, instagramUsername, facebookPageId);
  return getUser(instagramAccountId)!;
}

export function updateUser(
  instagramAccountId: string,
  instagramUsername: string | null,
  facebookPageId: string | null
): void {
  const stmt = db.prepare(`
    UPDATE users
    SET instagram_username = ?, facebook_page_id = ?, updated_at = CURRENT_TIMESTAMP
    WHERE instagram_account_id = ?
  `);
  stmt.run(instagramUsername, facebookPageId, instagramAccountId);
}

// ============================================================
// TOKEN OPERATIONS
// ============================================================

export interface Token {
  id: number;
  user_id: number;
  user_access_token: string;
  page_access_token: string;
  user_token_expires_at: string;
  is_valid: number;
  invalid_reason: string | null;
  created_at: string;
  updated_at: string;
}

export function getToken(userId: number): Token | undefined {
  const stmt = db.prepare(`
    SELECT * FROM tokens
    WHERE user_id = ? AND is_valid = 1
    ORDER BY created_at DESC
    LIMIT 1
  `);
  return stmt.get(userId) as Token | undefined;
}

export function saveToken(
  userId: number,
  userAccessToken: string,
  pageAccessToken: string,
  expiresAt: Date
): Token {
  const stmt = db.prepare(`
    INSERT INTO tokens (user_id, user_access_token, page_access_token, user_token_expires_at)
    VALUES (?, ?, ?, ?)
  `);
  const result = stmt.run(
    userId,
    userAccessToken,
    pageAccessToken,
    expiresAt.toISOString()
  );
  return {
    id: Number(result.lastInsertRowid),
    user_id: userId,
    user_access_token: userAccessToken,
    page_access_token: pageAccessToken,
    user_token_expires_at: expiresAt.toISOString(),
    is_valid: 1,
    invalid_reason: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
}

export function updateToken(
  tokenId: number,
  userAccessToken: string,
  pageAccessToken: string,
  expiresAt: Date
): void {
  const stmt = db.prepare(`
    UPDATE tokens
    SET user_access_token = ?, page_access_token = ?, user_token_expires_at = ?, updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
  `);
  stmt.run(userAccessToken, pageAccessToken, expiresAt.toISOString(), tokenId);
}

export function invalidateToken(tokenId: number, reason: string): void {
  const stmt = db.prepare(`
    UPDATE tokens
    SET is_valid = 0, invalid_reason = ?, updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
  `);
  stmt.run(reason, tokenId);
}

// ============================================================
// INSIGHTS OPERATIONS
// ============================================================

export interface Insight {
  id: number;
  user_id: number;
  metric_name: string;
  metric_value: number | null;
  period: string | null;
  collected_at: string;
  created_at: string;
}

export function saveInsight(
  userId: number,
  metricName: string,
  metricValue: number | null,
  period: string | null,
  collectedAt: Date
): void {
  const stmt = db.prepare(`
    INSERT INTO insights (user_id, metric_name, metric_value, period, collected_at)
    VALUES (?, ?, ?, ?, ?)
  `);
  stmt.run(userId, metricName, metricValue, period, collectedAt.toISOString());
}

export function saveInsightsBatch(
  userId: number,
  insights: Array<{
    metricName: string;
    metricValue: number | null;
    period: string | null;
  }>,
  collectedAt: Date
): void {
  const insert = db.prepare(`
    INSERT INTO insights (user_id, metric_name, metric_value, period, collected_at)
    VALUES (?, ?, ?, ?, ?)
  `);

  const transaction = db.transaction((rows: typeof insights) => {
    for (const row of rows) {
      insert.run(
        userId,
        row.metricName,
        row.metricValue,
        row.period,
        collectedAt.toISOString()
      );
    }
  });

  transaction(insights);
}

// ============================================================
// AUDIENCE DATA OPERATIONS
// ============================================================

export interface AudienceData {
  id: number;
  user_id: number;
  metric_name: string;
  metric_value: string;
  collected_at: string;
  created_at: string;
}

export function saveAudienceData(
  userId: number,
  metricName: string,
  metricValue: object,
  collectedAt: Date
): void {
  const stmt = db.prepare(`
    INSERT INTO audience_data (user_id, metric_name, metric_value, collected_at)
    VALUES (?, ?, ?, ?)
  `);
  stmt.run(userId, metricName, JSON.stringify(metricValue), collectedAt.toISOString());
}

export function saveAudienceDataBatch(
  userId: number,
  audienceData: Array<{
    metricName: string;
    metricValue: object;
  }>,
  collectedAt: Date
): void {
  const insert = db.prepare(`
    INSERT INTO audience_data (user_id, metric_name, metric_value, collected_at)
    VALUES (?, ?, ?, ?)
  `);

  const transaction = db.transaction((rows: typeof audienceData) => {
    for (const row of rows) {
      insert.run(
        userId,
        row.metricName,
        JSON.stringify(row.metricValue),
        collectedAt.toISOString()
      );
    }
  });

  transaction(audienceData);
}

// ============================================================
// COLLECTION LOG OPERATIONS
// ============================================================

export interface CollectionLog {
  id: number;
  user_id: number;
  collection_type: string;
  status: string;
  error_message: string | null;
  requests_made: number;
  created_at: string;
}

export function logCollection(
  userId: number,
  collectionType: string,
  status: string,
  requestsMade: number,
  errorMessage: string | null = null
): void {
  const stmt = db.prepare(`
    INSERT INTO collection_log (user_id, collection_type, status, error_message, requests_made)
    VALUES (?, ?, ?, ?, ?)
  `);
  stmt.run(userId, collectionType, status, errorMessage, requestsMade);
}

// Export database instance for advanced queries
export { db };
