import { createClient, Client } from '@libsql/client';
import { readFileSync } from 'fs';
import { join } from 'path';
import { config } from '../config';

// Initialize database client
export const db: Client = createClient({
  url: config.databaseUrl,
  authToken: config.databaseAuthToken,
});

// Initialize schema on first run
export async function initializeDatabase(): Promise<void> {
  const schemaPath = join(__dirname, 'schema.sql');
  const schema = readFileSync(schemaPath, 'utf-8');

  // Split schema into individual statements and execute each
  const statements = schema
    .split(';')
    .map(s => s.trim())
    .filter(s => s.length > 0);

  for (const statement of statements) {
    await db.execute(statement);
  }
}

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

export async function getUser(instagramAccountId: string): Promise<User | undefined> {
  const result = await db.execute({
    sql: 'SELECT * FROM users WHERE instagram_account_id = ?',
    args: [instagramAccountId],
  });
  return result.rows[0] as unknown as User | undefined;
}

export async function createUser(
  instagramAccountId: string,
  instagramUsername: string | null,
  facebookPageId: string | null
): Promise<User> {
  await db.execute({
    sql: `INSERT INTO users (instagram_account_id, instagram_username, facebook_page_id)
          VALUES (?, ?, ?)`,
    args: [instagramAccountId, instagramUsername, facebookPageId],
  });
  return (await getUser(instagramAccountId))!;
}

export async function updateUser(
  instagramAccountId: string,
  instagramUsername: string | null,
  facebookPageId: string | null
): Promise<void> {
  await db.execute({
    sql: `UPDATE users
          SET instagram_username = ?, facebook_page_id = ?, updated_at = CURRENT_TIMESTAMP
          WHERE instagram_account_id = ?`,
    args: [instagramUsername, facebookPageId, instagramAccountId],
  });
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

export async function getToken(userId: number): Promise<Token | undefined> {
  const result = await db.execute({
    sql: `SELECT * FROM tokens
          WHERE user_id = ? AND is_valid = 1
          ORDER BY created_at DESC
          LIMIT 1`,
    args: [userId],
  });
  return result.rows[0] as unknown as Token | undefined;
}

export async function saveToken(
  userId: number,
  userAccessToken: string,
  pageAccessToken: string,
  expiresAt: Date
): Promise<Token> {
  const result = await db.execute({
    sql: `INSERT INTO tokens (user_id, user_access_token, page_access_token, user_token_expires_at)
          VALUES (?, ?, ?, ?)`,
    args: [userId, userAccessToken, pageAccessToken, expiresAt.toISOString()],
  });
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

export async function updateToken(
  tokenId: number,
  userAccessToken: string,
  pageAccessToken: string,
  expiresAt: Date
): Promise<void> {
  await db.execute({
    sql: `UPDATE tokens
          SET user_access_token = ?, page_access_token = ?, user_token_expires_at = ?, updated_at = CURRENT_TIMESTAMP
          WHERE id = ?`,
    args: [userAccessToken, pageAccessToken, expiresAt.toISOString(), tokenId],
  });
}

export async function invalidateToken(tokenId: number, reason: string): Promise<void> {
  await db.execute({
    sql: `UPDATE tokens
          SET is_valid = 0, invalid_reason = ?, updated_at = CURRENT_TIMESTAMP
          WHERE id = ?`,
    args: [reason, tokenId],
  });
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

export async function saveInsight(
  userId: number,
  metricName: string,
  metricValue: number | null,
  period: string | null,
  collectedAt: Date
): Promise<void> {
  await db.execute({
    sql: `INSERT INTO insights (user_id, metric_name, metric_value, period, collected_at)
          VALUES (?, ?, ?, ?, ?)`,
    args: [userId, metricName, metricValue, period, collectedAt.toISOString()],
  });
}

export async function saveInsightsBatch(
  userId: number,
  insights: Array<{
    metricName: string;
    metricValue: number | null;
    period: string | null;
  }>,
  collectedAt: Date
): Promise<void> {
  const statements = insights.map(row => ({
    sql: `INSERT INTO insights (user_id, metric_name, metric_value, period, collected_at)
          VALUES (?, ?, ?, ?, ?)`,
    args: [userId, row.metricName, row.metricValue, row.period, collectedAt.toISOString()],
  }));

  await db.batch(statements);
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

export async function saveAudienceData(
  userId: number,
  metricName: string,
  metricValue: object,
  collectedAt: Date
): Promise<void> {
  await db.execute({
    sql: `INSERT INTO audience_data (user_id, metric_name, metric_value, collected_at)
          VALUES (?, ?, ?, ?)`,
    args: [userId, metricName, JSON.stringify(metricValue), collectedAt.toISOString()],
  });
}

export async function saveAudienceDataBatch(
  userId: number,
  audienceData: Array<{
    metricName: string;
    metricValue: object;
  }>,
  collectedAt: Date
): Promise<void> {
  const statements = audienceData.map(row => ({
    sql: `INSERT INTO audience_data (user_id, metric_name, metric_value, collected_at)
          VALUES (?, ?, ?, ?)`,
    args: [userId, row.metricName, JSON.stringify(row.metricValue), collectedAt.toISOString()],
  }));

  await db.batch(statements);
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

export async function logCollection(
  userId: number,
  collectionType: string,
  status: string,
  requestsMade: number,
  errorMessage: string | null = null
): Promise<void> {
  await db.execute({
    sql: `INSERT INTO collection_log (user_id, collection_type, status, error_message, requests_made)
          VALUES (?, ?, ?, ?, ?)`,
    args: [userId, collectionType, status, errorMessage, requestsMade],
  });
}
