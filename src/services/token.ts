import { config } from '../config';
import * as oauth from './oauth';
import { db, getToken, saveToken, invalidateToken } from '../db/connection';
import type { Token } from '../db/connection';

// Get all tokens expiring within specified days
export async function getExpiringTokens(daysThreshold: number = 10): Promise<Token[]> {
  const thresholdDate = new Date();
  thresholdDate.setDate(thresholdDate.getDate() + daysThreshold);

  const result = await db.execute({
    sql: `SELECT * FROM tokens
          WHERE is_valid = 1
          AND user_token_expires_at < ?
          ORDER BY user_token_expires_at ASC`,
    args: [thresholdDate.toISOString()],
  });

  return result.rows as unknown as Token[];
}

// Refresh a single user's token
export async function refreshUserToken(token: Token): Promise<boolean> {
  try {
    // Exchange current long-lived token for new one
    const { token: newUserToken, expiresIn } = await oauth.exchangeForLongLivedToken(token.user_access_token);

    // Get new page token
    const { pageId, pageToken: newPageToken } = await oauth.getPageAccessToken(newUserToken);

    // Calculate new expiration
    const newExpiresAt = new Date(Date.now() + expiresIn * 1000);

    // Save new tokens
    await saveToken(token.user_id, newUserToken, newPageToken, newExpiresAt);

    console.log(`Token refreshed for user ${token.user_id}, expires: ${newExpiresAt.toISOString()}`);
    return true;
  } catch (error: any) {
    console.error(`Token refresh failed for user ${token.user_id}:`, error.message);

    // Check if token is invalid (auth error)
    if (error.response?.data?.error?.code === 190) {
      await invalidateToken(token.id, 'Token expired or revoked by user');
    }

    return false;
  }
}

// Refresh all expiring tokens with delay between requests
export async function refreshAllExpiringTokens(): Promise<{ refreshed: number; failed: number }> {
  const expiringTokens = await getExpiringTokens(10);
  let refreshed = 0;
  let failed = 0;

  for (const token of expiringTokens) {
    const success = await refreshUserToken(token);
    if (success) refreshed++;
    else failed++;

    // 500ms delay between users
    await new Promise(resolve => setTimeout(resolve, 500));
  }

  return { refreshed, failed };
}
