import { db, saveInsight, saveAudienceData, logCollection, User, Token } from '../db/connection';
import { fetchInsights, fetchAudienceData, rateLimiter } from '../services/instagram';

// Get all users with valid tokens
function getActiveUsers(): Array<{ user: User; token: Token }> {
  const stmt = db.prepare(`
    SELECT u.*, t.*
    FROM users u
    JOIN tokens t ON u.id = t.user_id
    WHERE t.is_valid = 1
    ORDER BY u.id
  `);
  return stmt.all().map((row: any) => ({
    user: {
      id: row.id,
      instagram_account_id: row.instagram_account_id,
      instagram_username: row.instagram_username,
      facebook_page_id: row.facebook_page_id,
      created_at: row.created_at,
      updated_at: row.updated_at
    },
    token: {
      id: row.id,
      user_id: row.user_id,
      user_access_token: row.user_access_token,
      page_access_token: row.page_access_token,
      user_token_expires_at: row.user_token_expires_at,
      is_valid: row.is_valid,
      invalid_reason: row.invalid_reason,
      created_at: row.created_at,
      updated_at: row.updated_at
    }
  }));
}

export async function runInsightsCollectionJob(collectAudience: boolean = false) {
  console.log('Starting insights collection...');
  const users = getActiveUsers();
  let success = 0, failed = 0;

  for (const { user, token } of users) {
    try {
      // Check rate limit
      if (!rateLimiter.canMakeRequest(user.instagram_account_id)) {
        console.log(`Rate limited for user ${user.id}`);
        continue;
      }

      // Fetch daily insights
      const insights = await fetchInsights(
        user.instagram_account_id,
        token.page_access_token,
        ['impressions', 'reach', 'accounts_engaged', 'follower_count'],
        'day'
      );

      // Save each metric
      const collectedAt = new Date();
      for (const metric of insights.data || []) {
        const value = metric.values?.[0]?.value || 0;
        const numValue = typeof value === 'number' ? value : 0;
        saveInsight(user.id, metric.name, numValue, metric.period, collectedAt);
      }

      // Fetch audience data (daily only)
      if (collectAudience) {
        const audienceData = await fetchAudienceData(user.instagram_account_id, token.page_access_token);
        for (const metric of audienceData.data || []) {
          const value = metric.values?.[0]?.value || {};
          saveAudienceData(user.id, metric.name, value, collectedAt);
        }
      }

      logCollection(user.id, collectAudience ? 'audience' : 'insights', 'success', 1, null);
      success++;
    } catch (error: any) {
      console.error(`Collection failed for user ${user.id}:`, error.message);
      logCollection(user.id, 'insights', 'failed', 0, error.message);
      failed++;
    }

    // 500ms delay between users
    await new Promise(r => setTimeout(r, 500));
  }

  console.log(`Collection complete: ${success} success, ${failed} failed`);
  return { success, failed };
}
