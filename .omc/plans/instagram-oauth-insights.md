# Instagram OAuth + Insights Collection System

## Overview

Build a system that allows influencers to connect their Instagram Business/Creator accounts via OAuth, automatically manages token refresh, and collects Instagram Insights data on a scheduled basis.

---

## 1. Project Structure

```
urlinsta/
├── .env                          # Environment variables (secrets)
├── .env.example                  # Template for env vars
├── package.json                  # Node.js dependencies
├── tsconfig.json                 # TypeScript configuration
├── vercel.json                   # Vercel deployment config
├── src/
│   ├── index.ts                  # Express app entry point
│   ├── config.ts                 # Configuration loader
│   ├── db/
│   │   ├── schema.sql            # SQLite schema
│   │   ├── connection.ts         # Database connection
│   │   └── migrations/           # Future migrations
│   ├── routes/
│   │   ├── auth.ts               # OAuth routes
│   │   ├── insights.ts           # Insights API routes
│   │   ├── cron.ts               # Cron job endpoints for Vercel
│   │   └── health.ts             # Health check endpoint
│   ├── services/
│   │   ├── oauth.ts              # OAuth flow logic
│   │   ├── token.ts              # Token management & refresh
│   │   ├── instagram.ts          # Instagram Graph API client
│   │   └── insights-collector.ts # Scheduled insights fetcher
│   ├── jobs/
│   │   ├── scheduler.ts          # Cron job setup
│   │   ├── refresh-tokens.ts     # Token refresh job
│   │   └── collect-insights.ts   # Insights collection job
│   └── types/
│       └── index.ts              # TypeScript type definitions
├── public/
│   └── index.html                # Single-page frontend
└── data/
    └── urlinsta.db               # SQLite database file
```

---

## 2. Database Schema

### File: `src/db/schema.sql`

```sql
-- Users table: stores connected Instagram accounts
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instagram_user_id TEXT UNIQUE NOT NULL,
    instagram_username TEXT,
    facebook_page_id TEXT,
    facebook_page_name TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tokens table: stores BOTH User Access Token and Page Access Token
-- User token is needed for refresh; Page token is used for API calls
CREATE TABLE IF NOT EXISTS tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    -- Long-lived User Access Token (needed for refresh)
    user_access_token TEXT NOT NULL,
    user_token_expires_at DATETIME NOT NULL,
    -- Page Access Token (used for Instagram API calls)
    -- Page tokens inherit long-lived status and don't expire while user token is valid
    page_access_token TEXT NOT NULL,
    -- Metadata
    last_refreshed_at DATETIME,
    is_valid BOOLEAN DEFAULT 1,
    invalid_reason TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

-- Insights table: stores collected Instagram insights
CREATE TABLE IF NOT EXISTS insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    metric_name TEXT NOT NULL,
    metric_value INTEGER,
    period TEXT NOT NULL,
    end_time DATETIME,
    collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, metric_name, period, end_time)
);

-- Audience demographics table
CREATE TABLE IF NOT EXISTS audience_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    demographic_type TEXT NOT NULL,  -- 'city', 'country', 'gender_age'
    dimension_key TEXT NOT NULL,     -- e.g., 'US', 'M.25-34', 'New York, CA'
    dimension_value INTEGER,
    collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, demographic_type, dimension_key, collected_at)
);

-- Collection log: tracks job runs and errors
CREATE TABLE IF NOT EXISTS collection_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    job_type TEXT NOT NULL,          -- 'insights', 'token_refresh'
    status TEXT NOT NULL,            -- 'success', 'failed', 'skipped'
    error_message TEXT,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_tokens_expires_at ON tokens(user_token_expires_at);
CREATE INDEX IF NOT EXISTS idx_tokens_valid ON tokens(is_valid);
CREATE INDEX IF NOT EXISTS idx_insights_user_collected ON insights(user_id, collected_at);
CREATE INDEX IF NOT EXISTS idx_collection_log_status ON collection_log(job_type, status);
```

---

## 3. API Endpoints

### Authentication Routes (`/api/auth/*`)

| Method | Endpoint | Description | Request | Response |
|--------|----------|-------------|---------|----------|
| GET | `/api/auth/login` | Redirect to Facebook OAuth | - | 302 Redirect |
| GET | `/api/auth/callback` | Handle OAuth callback | `?code=...&state=...` | 302 Redirect to success/error page |
| GET | `/api/auth/status` | Check if user is connected | - | `{ connected: boolean, username?: string }` |
| POST | `/api/auth/disconnect` | Remove user and tokens | `{ instagram_user_id: string }` | `{ success: boolean }` |

### Insights Routes (`/api/insights/*`)

| Method | Endpoint | Description | Request | Response |
|--------|----------|-------------|---------|----------|
| GET | `/api/insights/:userId` | Get stored insights for user | `?from=date&to=date` | `{ insights: [...] }` |
| GET | `/api/insights/:userId/audience` | Get audience demographics | - | `{ city: [...], country: [...], gender_age: [...] }` |
| POST | `/api/insights/:userId/refresh` | Manually trigger collection | - | `{ success: boolean, collected: number }` |

### Cron Routes (`/api/cron/*`) - Vercel Cron Endpoints

| Method | Endpoint | Description | Response |
|--------|----------|-------------|----------|
| GET | `/api/cron/refresh-tokens` | Trigger token refresh job | `{ refreshed: number, failed: number }` |
| GET | `/api/cron/collect-insights` | Trigger insights collection | `{ collected: number, failed: number }` |
| GET | `/api/cron/collect-audience` | Trigger audience data collection | `{ collected: number, failed: number }` |

### Health Routes (`/api/health/*`)

| Method | Endpoint | Description | Response |
|--------|----------|-------------|----------|
| GET | `/api/health` | Basic health check | `{ status: 'ok', timestamp: string }` |
| GET | `/api/health/db` | Database connectivity | `{ status: 'ok', users_count: number }` |

---

## 4. OAuth Flow Implementation (CORRECTED - Facebook Login Flow)

### Step-by-Step Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Browser   │     │   Backend   │     │  Facebook   │     │  Instagram  │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │                   │
       │ 1. Click Login    │                   │                   │
       │──────────────────>│                   │                   │
       │                   │                   │                   │
       │ 2. Redirect to FB │                   │                   │
       │<──────────────────│                   │                   │
       │                   │                   │                   │
       │ 3. FB Login Page  │                   │                   │
       │───────────────────────────────────────>                   │
       │                   │                   │                   │
       │ 4. User Grants    │                   │                   │
       │<──────────────────────────────────────│                   │
       │                   │                   │                   │
       │ 5. Callback w/code│                   │                   │
       │──────────────────>│                   │                   │
       │                   │                   │                   │
       │                   │ 6. Exchange code  │                   │
       │                   │   for SHORT-LIVED │                   │
       │                   │   User Token      │                   │
       │                   │──────────────────>│                   │
       │                   │                   │                   │
       │                   │ 7. Short token    │                   │
       │                   │   (~1 hour)       │                   │
       │                   │<──────────────────│                   │
       │                   │                   │                   │
       │                   │ 8. Exchange for   │                   │
       │                   │   LONG-LIVED      │                   │
       │                   │   User Token      │                   │
       │                   │──────────────────>│                   │
       │                   │                   │                   │
       │                   │ 9. Long-lived     │                   │
       │                   │   token (~60 days)│                   │
       │                   │<──────────────────│                   │
       │                   │                   │                   │
       │                   │ 10. Get Pages     │                   │
       │                   │   (includes Page  │                   │
       │                   │    Access Tokens) │                   │
       │                   │──────────────────>│                   │
       │                   │                   │                   │
       │                   │ 11. Page tokens   │                   │
       │                   │   (inherit long-  │                   │
       │                   │    lived status)  │                   │
       │                   │<──────────────────│                   │
       │                   │                   │                   │
       │                   │ 12. Get IG Account│                   │
       │                   │   from Page       │                   │
       │                   │───────────────────────────────────────>
       │                   │                   │                   │
       │                   │ 13. IG Business   │                   │
       │                   │   Account ID      │                   │
       │                   │<──────────────────────────────────────│
       │                   │                   │                   │
       │                   │ 14. Store BOTH    │                   │
       │                   │   tokens in DB    │                   │
       │                   │                   │                   │
       │ 15. Success page  │                   │                   │
       │<──────────────────│                   │                   │
```

### OAuth Service Implementation Details

**File: `src/services/oauth.ts`**

```typescript
// IMPORTANT: This uses Facebook Login flow (NOT Instagram Basic Display API)
// Facebook Login is REQUIRED for Business/Creator accounts with insights access

const FB_API_VERSION = 'v18.0';
const FB_GRAPH_URL = `https://graph.facebook.com/${FB_API_VERSION}`;

// Required scopes for Instagram Insights access
const OAUTH_SCOPES = [
  'instagram_basic',              // Read IG profile info
  'instagram_manage_insights',    // Read IG insights
  'pages_show_list',              // List Facebook Pages
  'pages_read_engagement',        // Read Page engagement data
  // Optional: 'business_management' - Add if app requires business asset access
].join(',');

// 1. generateAuthUrl(): string
//    - Build Facebook OAuth URL (NOT Instagram!)
//    - URL: https://www.facebook.com/v18.0/dialog/oauth
//    - Params:
//      - client_id: FB_APP_ID
//      - redirect_uri: CALLBACK_URL
//      - scope: instagram_basic,instagram_manage_insights,pages_show_list,pages_read_engagement
//      - state: random string for CSRF protection (store in session/cookie)
//      - response_type: code

function generateAuthUrl(state: string): string {
  const params = new URLSearchParams({
    client_id: process.env.FB_APP_ID!,
    redirect_uri: process.env.OAUTH_REDIRECT_URI!,
    scope: OAUTH_SCOPES,
    state: state,
    response_type: 'code',
  });
  return `https://www.facebook.com/${FB_API_VERSION}/dialog/oauth?${params}`;
}

// 2. exchangeCodeForShortLivedToken(code: string): Promise<ShortLivedToken>
//    - Exchange authorization code for SHORT-LIVED User Access Token
//    - Endpoint: https://graph.facebook.com/v18.0/oauth/access_token
//    - This token expires in ~1 hour

async function exchangeCodeForShortLivedToken(code: string): Promise<{
  access_token: string;
  token_type: string;
  expires_in: number;
}> {
  const params = new URLSearchParams({
    client_id: process.env.FB_APP_ID!,
    client_secret: process.env.FB_APP_SECRET!,
    redirect_uri: process.env.OAUTH_REDIRECT_URI!,
    code: code,
  });

  const response = await fetch(`${FB_GRAPH_URL}/oauth/access_token?${params}`);
  if (!response.ok) {
    const error = await response.json();
    throw new Error(`Failed to exchange code: ${JSON.stringify(error)}`);
  }
  return response.json();
}

// 3. exchangeForLongLivedUserToken(shortToken: string): Promise<LongLivedToken>
//    - Exchange short-lived token for LONG-LIVED User Access Token
//    - Endpoint: https://graph.facebook.com/v18.0/oauth/access_token
//    - grant_type: fb_exchange_token (NOT ig_exchange_token!)
//    - This token expires in ~60 days

async function exchangeForLongLivedUserToken(shortToken: string): Promise<{
  access_token: string;
  token_type: string;
  expires_in: number; // ~5184000 seconds = 60 days
}> {
  const params = new URLSearchParams({
    grant_type: 'fb_exchange_token',
    client_id: process.env.FB_APP_ID!,
    client_secret: process.env.FB_APP_SECRET!,
    fb_exchange_token: shortToken,
  });

  const response = await fetch(`${FB_GRAPH_URL}/oauth/access_token?${params}`);
  if (!response.ok) {
    const error = await response.json();
    throw new Error(`Failed to exchange for long-lived token: ${JSON.stringify(error)}`);
  }
  return response.json();
}

// 4. getPageAccessTokens(userToken: string): Promise<FacebookPage[]>
//    - Get Facebook Pages the user manages (includes Page Access Tokens)
//    - Endpoint: https://graph.facebook.com/v18.0/me/accounts
//    - Page tokens AUTOMATICALLY inherit long-lived status from user token
//    - Page tokens DO NOT EXPIRE as long as user token is valid

async function getPageAccessTokens(userToken: string): Promise<Array<{
  id: string;
  name: string;
  access_token: string; // This is a long-lived Page Access Token
}>> {
  const response = await fetch(
    `${FB_GRAPH_URL}/me/accounts?access_token=${userToken}`
  );
  if (!response.ok) {
    const error = await response.json();
    throw new Error(`Failed to get pages: ${JSON.stringify(error)}`);
  }
  const data = await response.json();
  return data.data || [];
}

// 5. getInstagramBusinessAccount(pageId: string, pageToken: string): Promise<IGAccount | null>
//    - Get Instagram Business Account connected to a Facebook Page
//    - Endpoint: https://graph.facebook.com/v18.0/{page-id}?fields=instagram_business_account

async function getInstagramBusinessAccount(
  pageId: string,
  pageToken: string
): Promise<{ id: string; username?: string } | null> {
  const response = await fetch(
    `${FB_GRAPH_URL}/${pageId}?fields=instagram_business_account&access_token=${pageToken}`
  );
  if (!response.ok) {
    return null;
  }
  const data = await response.json();

  if (!data.instagram_business_account) {
    return null;
  }

  // Get username for the Instagram account
  const igResponse = await fetch(
    `${FB_GRAPH_URL}/${data.instagram_business_account.id}?fields=username&access_token=${pageToken}`
  );
  const igData = await igResponse.json();

  return {
    id: data.instagram_business_account.id,
    username: igData.username,
  };
}

// 6. discoverInstagramAccount(userToken: string): Promise<DiscoveryResult>
//    - Complete flow: Get pages -> Find first IG account -> Return both tokens

interface DiscoveryResult {
  instagramUserId: string;
  instagramUsername: string;
  facebookPageId: string;
  facebookPageName: string;
  pageAccessToken: string;  // For API calls
  userAccessToken: string;  // For refresh
}

async function discoverInstagramAccount(
  userLongLivedToken: string
): Promise<DiscoveryResult> {
  // Get all pages
  const pages = await getPageAccessTokens(userLongLivedToken);

  if (pages.length === 0) {
    throw new Error('No Facebook Pages found. User must have a Facebook Page.');
  }

  // Find first page with an Instagram Business Account
  for (const page of pages) {
    const igAccount = await getInstagramBusinessAccount(page.id, page.access_token);
    if (igAccount) {
      return {
        instagramUserId: igAccount.id,
        instagramUsername: igAccount.username || '',
        facebookPageId: page.id,
        facebookPageName: page.name,
        pageAccessToken: page.access_token,
        userAccessToken: userLongLivedToken,
      };
    }
  }

  throw new Error(
    'No Instagram Business/Creator account found. ' +
    'User must connect an Instagram Business or Creator account to their Facebook Page.'
  );
}

// 7. handleCallback(code: string, state: string): Promise<User>
//    - Complete OAuth callback handler

async function handleCallback(code: string, state: string): Promise<User> {
  // Validate state matches stored state (CSRF protection)
  // ... state validation logic ...

  // Step 1: Exchange code for short-lived token
  const shortLivedToken = await exchangeCodeForShortLivedToken(code);

  // Step 2: Exchange for long-lived user token
  const longLivedToken = await exchangeForLongLivedUserToken(shortLivedToken.access_token);
  const userTokenExpiresAt = new Date(Date.now() + longLivedToken.expires_in * 1000);

  // Step 3: Discover Instagram account (includes page token)
  const discovery = await discoverInstagramAccount(longLivedToken.access_token);

  // Step 4: Store user and BOTH tokens in database
  const user = await db.run(`
    INSERT INTO users (instagram_user_id, instagram_username, facebook_page_id, facebook_page_name)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(instagram_user_id) DO UPDATE SET
      instagram_username = excluded.instagram_username,
      facebook_page_id = excluded.facebook_page_id,
      facebook_page_name = excluded.facebook_page_name,
      updated_at = CURRENT_TIMESTAMP
    RETURNING *
  `, [discovery.instagramUserId, discovery.instagramUsername, discovery.facebookPageId, discovery.facebookPageName]);

  await db.run(`
    INSERT INTO tokens (user_id, user_access_token, user_token_expires_at, page_access_token)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(user_id) DO UPDATE SET
      user_access_token = excluded.user_access_token,
      user_token_expires_at = excluded.user_token_expires_at,
      page_access_token = excluded.page_access_token,
      is_valid = 1,
      invalid_reason = NULL,
      last_refreshed_at = CURRENT_TIMESTAMP,
      updated_at = CURRENT_TIMESTAMP
  `, [user.id, discovery.userAccessToken, userTokenExpiresAt.toISOString(), discovery.pageAccessToken]);

  return user;
}
```

---

## 5. Token Refresh Logic (CORRECTED)

### Token Architecture

| Token Type | Purpose | Expiration | Refresh Method |
|------------|---------|------------|----------------|
| **User Access Token** | Used for refresh operations | ~60 days | `fb_exchange_token` grant |
| **Page Access Token** | Used for Instagram API calls | Never expires* | Regenerated when user token is refreshed |

*Page tokens do not expire as long as the user's long-lived token is valid.

### Refresh Strategy

1. **User long-lived tokens expire in ~60 days**
2. **Schedule refresh at 50 days** (10-day safety buffer)
3. **Run refresh job every 6 hours** to catch any tokens needing refresh
4. **On refresh**: Get new user token, then re-fetch page tokens
5. **On failure**: Retry with exponential backoff, then mark token as invalid

### File: `src/services/token.ts`

```typescript
const FB_API_VERSION = 'v18.0';
const FB_GRAPH_URL = `https://graph.facebook.com/${FB_API_VERSION}`;

// Refresh a user's long-lived token
// IMPORTANT: Use fb_exchange_token on graph.facebook.com (NOT graph.instagram.com!)
async function refreshUserToken(currentUserToken: string): Promise<{
  access_token: string;
  expires_in: number;
}> {
  const params = new URLSearchParams({
    grant_type: 'fb_exchange_token',
    client_id: process.env.FB_APP_ID!,
    client_secret: process.env.FB_APP_SECRET!,
    fb_exchange_token: currentUserToken,
  });

  const response = await fetch(`${FB_GRAPH_URL}/oauth/access_token?${params}`);
  if (!response.ok) {
    const error = await response.json();
    throw new Error(`Token refresh failed: ${JSON.stringify(error)}`);
  }
  return response.json();
}

// After refreshing user token, we need to get fresh page tokens
async function refreshPageToken(
  userToken: string,
  pageId: string
): Promise<string> {
  const response = await fetch(
    `${FB_GRAPH_URL}/me/accounts?access_token=${userToken}`
  );
  if (!response.ok) {
    throw new Error('Failed to fetch pages for token refresh');
  }
  const data = await response.json();
  const page = data.data.find((p: any) => p.id === pageId);

  if (!page) {
    throw new Error(`Page ${pageId} not found. User may have revoked access.`);
  }

  return page.access_token;
}
```

### File: `src/jobs/refresh-tokens.ts`

```typescript
// Exponential backoff helper
async function withExponentialBackoff<T>(
  operation: () => Promise<T>,
  maxRetries: number = 3,
  baseDelayMs: number = 1000
): Promise<T> {
  let lastError: Error;

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = error as Error;

      // Don't retry on auth errors (user revoked, token invalid)
      if (isAuthError(error)) {
        throw error;
      }

      // Exponential backoff: 1s, 2s, 4s, 8s...
      const delay = baseDelayMs * Math.pow(2, attempt);
      await sleep(delay);
    }
  }

  throw lastError!;
}

function isAuthError(error: any): boolean {
  const code = error?.error?.code;
  return code === 190 || code === 102; // Invalid/expired token or session
}

// Token refresh job
async function refreshTokensJob(): Promise<{ refreshed: number; failed: number }> {
  let refreshed = 0;
  let failed = 0;

  // Find tokens expiring within 10 days that are still valid
  const tokensToRefresh = await db.query(`
    SELECT t.*, u.instagram_user_id, u.facebook_page_id
    FROM tokens t
    JOIN users u ON t.user_id = u.id
    WHERE t.user_token_expires_at < datetime('now', '+10 days')
    AND t.is_valid = 1
  `);

  for (const token of tokensToRefresh) {
    try {
      await withExponentialBackoff(async () => {
        // 1. Refresh the user access token
        const newUserToken = await refreshUserToken(token.user_access_token);
        const newExpiresAt = new Date(Date.now() + newUserToken.expires_in * 1000);

        // 2. Get fresh page token (inherits long-lived status automatically)
        const newPageToken = await refreshPageToken(
          newUserToken.access_token,
          token.facebook_page_id
        );

        // 3. Update database with BOTH new tokens
        await db.run(`
          UPDATE tokens
          SET user_access_token = ?,
              user_token_expires_at = ?,
              page_access_token = ?,
              last_refreshed_at = datetime('now'),
              updated_at = datetime('now')
          WHERE id = ?
        `, [newUserToken.access_token, newExpiresAt.toISOString(), newPageToken, token.id]);
      });

      await logCollection(token.user_id, 'token_refresh', 'success');
      refreshed++;

    } catch (error) {
      failed++;
      const errorMessage = error instanceof Error ? error.message : String(error);

      // Mark token as invalid if it's an auth error
      if (isAuthError(error)) {
        await db.run(`
          UPDATE tokens
          SET is_valid = 0,
              invalid_reason = ?,
              updated_at = datetime('now')
          WHERE id = ?
        `, [errorMessage, token.id]);

        // TODO: Notify user that their token is invalid
        // await notifyUserTokenInvalid(token.user_id, errorMessage);
      }

      await logCollection(token.user_id, 'token_refresh', 'failed', errorMessage);
    }
  }

  return { refreshed, failed };
}
```

### Cron Schedule

```typescript
// File: src/jobs/scheduler.ts
import cron from 'node-cron';

// Token refresh: every 6 hours
cron.schedule('0 */6 * * *', refreshTokensJob);

// Insights collection: hourly at minute 15
cron.schedule('15 * * * *', collectInsightsJob);

// Audience data: daily at 3 AM
cron.schedule('0 3 * * *', collectAudienceJob);
```

---

## 6. Insights Collection

### What Data to Collect

| Metric | Period | Frequency | Description |
|--------|--------|-----------|-------------|
| `impressions` | day | Hourly | Total impressions |
| `reach` | day | Hourly | Unique accounts reached |
| `accounts_engaged` | day | Hourly | Accounts that engaged |
| `follower_count` | lifetime | Hourly | Current follower count |
| `audience_city` | lifetime | Daily | Top cities of followers |
| `audience_country` | lifetime | Daily | Top countries of followers |
| `audience_gender_age` | lifetime | Daily | Gender and age breakdown |

### File: `src/jobs/collect-insights.ts`

```typescript
// Core insights collection implementation:

const HOURLY_METRICS = ['impressions', 'reach', 'accounts_engaged'];
const DAILY_METRICS = ['audience_city', 'audience_country', 'audience_gender_age'];

async function collectInsightsJob(): Promise<{ collected: number; failed: number }> {
  let collected = 0;
  let failed = 0;

  const users = await db.query(`
    SELECT u.*, t.page_access_token
    FROM users u
    JOIN tokens t ON u.id = t.user_id
    WHERE t.is_valid = 1
  `);

  for (const user of users) {
    try {
      // Use PAGE access token for Instagram API calls
      const accessToken = user.page_access_token;

      // Collect time-series metrics with exponential backoff
      await withExponentialBackoff(async () => {
        const metricsUrl = `https://graph.facebook.com/v18.0/${user.instagram_user_id}/insights` +
          `?metric=${HOURLY_METRICS.join(',')}&period=day&access_token=${accessToken}`;

        const response = await fetch(metricsUrl);

        // Handle rate limiting
        if (response.status === 429) {
          const retryAfter = response.headers.get('Retry-After') || '60';
          throw new RateLimitError(`Rate limited. Retry after ${retryAfter}s`);
        }

        if (!response.ok) {
          const error = await response.json();
          throw new Error(`Insights API error: ${JSON.stringify(error)}`);
        }

        const data = await response.json();

        // Store each metric
        for (const metric of data.data) {
          for (const value of metric.values) {
            await db.run(`
              INSERT OR REPLACE INTO insights
              (user_id, metric_name, metric_value, period, end_time, collected_at)
              VALUES (?, ?, ?, ?, ?, datetime('now'))
            `, [user.id, metric.name, value.value, metric.period, value.end_time]);
          }
        }
      });

      // Get follower count separately
      await withExponentialBackoff(async () => {
        const userUrl = `https://graph.facebook.com/v18.0/${user.instagram_user_id}` +
          `?fields=followers_count&access_token=${accessToken}`;
        const response = await fetch(userUrl);

        if (response.status === 429) {
          throw new RateLimitError('Rate limited on user endpoint');
        }

        const userData = await response.json();

        await db.run(`
          INSERT INTO insights
          (user_id, metric_name, metric_value, period, collected_at)
          VALUES (?, 'follower_count', ?, 'lifetime', datetime('now'))
        `, [user.id, userData.followers_count]);
      });

      await logCollection(user.id, 'insights', 'success');
      collected++;

    } catch (error) {
      failed++;
      await logCollection(user.id, 'insights', 'failed',
        error instanceof Error ? error.message : String(error));
    }

    // Rate limit: wait 500ms between users (stay under 200/hr limit)
    await sleep(500);
  }

  return { collected, failed };
}

async function collectAudienceJob(): Promise<{ collected: number; failed: number }> {
  // Similar pattern but for audience demographics
  // These only need daily collection
}
```

### Rate Limit Handling with Exponential Backoff

```typescript
// Custom error for rate limiting
class RateLimitError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'RateLimitError';
  }
}

// Rate limit strategy:
// - 200 requests/hour per IG account
// - Batch requests where possible
// - Track request counts per user
// - Implement exponential backoff on 429 errors

const REQUEST_LIMIT = 180; // Leave buffer
const HOUR_MS = 60 * 60 * 1000;

class RateLimiter {
  private counts: Map<string, { count: number, resetAt: number }> = new Map();

  async checkLimit(userId: string): Promise<boolean> {
    const now = Date.now();
    const userLimit = this.counts.get(userId);

    if (!userLimit || now > userLimit.resetAt) {
      this.counts.set(userId, { count: 1, resetAt: now + HOUR_MS });
      return true;
    }

    if (userLimit.count >= REQUEST_LIMIT) {
      return false; // Rate limited
    }

    userLimit.count++;
    return true;
  }
}

// Exponential backoff with jitter for rate limit handling
async function withExponentialBackoff<T>(
  operation: () => Promise<T>,
  maxRetries: number = 3,
  baseDelayMs: number = 1000
): Promise<T> {
  let lastError: Error;

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = error as Error;

      // Check if it's a rate limit error
      const isRateLimit = error instanceof RateLimitError ||
        (error as any)?.status === 429;

      if (!isRateLimit && attempt === maxRetries - 1) {
        throw error;
      }

      // Exponential backoff with jitter: 1s, 2s, 4s + random 0-500ms
      const jitter = Math.random() * 500;
      const delay = baseDelayMs * Math.pow(2, attempt) + jitter;

      console.log(`Retry ${attempt + 1}/${maxRetries} after ${delay}ms`);
      await sleep(delay);
    }
  }

  throw lastError!;
}
```

---

## 7. Cron Endpoint Handlers

### File: `src/routes/cron.ts`

```typescript
import { Router } from 'express';
import { refreshTokensJob } from '../jobs/refresh-tokens';
import { collectInsightsJob } from '../jobs/collect-insights';
import { collectAudienceJob } from '../jobs/collect-insights';

const router = Router();

// Verify request is from Vercel Cron (optional security)
function verifyCronRequest(req: Request): boolean {
  const authHeader = req.headers.get('authorization');
  if (process.env.CRON_SECRET) {
    return authHeader === `Bearer ${process.env.CRON_SECRET}`;
  }
  // In development, allow all requests
  return process.env.NODE_ENV !== 'production';
}

// GET /api/cron/refresh-tokens
router.get('/refresh-tokens', async (req, res) => {
  if (!verifyCronRequest(req)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  try {
    const result = await refreshTokensJob();
    res.json({
      success: true,
      refreshed: result.refreshed,
      failed: result.failed,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    });
  }
});

// GET /api/cron/collect-insights
router.get('/collect-insights', async (req, res) => {
  if (!verifyCronRequest(req)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  try {
    const result = await collectInsightsJob();
    res.json({
      success: true,
      collected: result.collected,
      failed: result.failed,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    });
  }
});

// GET /api/cron/collect-audience
router.get('/collect-audience', async (req, res) => {
  if (!verifyCronRequest(req)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  try {
    const result = await collectAudienceJob();
    res.json({
      success: true,
      collected: result.collected,
      failed: result.failed,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    });
  }
});

export default router;
```

---

## 8. Implementation Order

### Phase 1: Core Setup (Tasks 1-4)

| # | Task | Files | Acceptance Criteria |
|---|------|-------|---------------------|
| 1 | Initialize Node.js project with TypeScript | `package.json`, `tsconfig.json` | `npm run build` succeeds |
| 2 | Set up SQLite database and schema | `src/db/schema.sql`, `src/db/connection.ts` | Tables created, can insert/query |
| 3 | Create Express app with health routes | `src/index.ts`, `src/routes/health.ts` | `GET /api/health` returns 200 |
| 4 | Create environment configuration | `.env.example`, `src/config.ts` | Config loads from env vars |

### Phase 2: OAuth Implementation (Tasks 5-8)

| # | Task | Files | Acceptance Criteria |
|---|------|-------|---------------------|
| 5 | Implement OAuth URL generation | `src/services/oauth.ts` | Correct FB OAuth URL generated |
| 6 | Implement token exchange flow (short -> long-lived) | `src/services/oauth.ts` | Can exchange code for long-lived user token |
| 7 | Implement IG account discovery + page tokens | `src/services/oauth.ts`, `src/services/instagram.ts` | Can find IG account and get page token |
| 8 | Create auth routes with callback | `src/routes/auth.ts` | Full OAuth flow works, stores BOTH tokens |

### Phase 3: Frontend (Task 9)

| # | Task | Files | Acceptance Criteria |
|---|------|-------|---------------------|
| 9 | Create single-page frontend | `public/index.html` | Login button works, shows status |

### Phase 4: Token Management (Tasks 10-11)

| # | Task | Files | Acceptance Criteria |
|---|------|-------|---------------------|
| 10 | Implement token refresh service | `src/services/token.ts` | Can refresh user token, updates page token |
| 11 | Create token refresh cron job | `src/jobs/refresh-tokens.ts`, `src/jobs/scheduler.ts` | Job runs on schedule with exponential backoff |

### Phase 5: Insights Collection (Tasks 12-14)

| # | Task | Files | Acceptance Criteria |
|---|------|-------|---------------------|
| 12 | Implement Instagram Graph API client | `src/services/instagram.ts` | Can fetch insights using page token |
| 13 | Create insights collection job | `src/jobs/collect-insights.ts` | Insights stored in DB with rate limit handling |
| 14 | Add insights API routes | `src/routes/insights.ts` | Can query stored insights |

### Phase 6: Deployment (Tasks 15-17)

| # | Task | Files | Acceptance Criteria |
|---|------|-------|---------------------|
| 15 | Create cron endpoint handlers | `src/routes/cron.ts` | All 3 cron endpoints work |
| 16 | Configure Vercel deployment | `vercel.json` | Deploys successfully |
| 17 | Add Vercel cron configuration | `vercel.json` | Cron jobs run in production |

---

## 9. Acceptance Criteria

### Overall System Verification

- [ ] **OAuth Flow**: User can click login, grant permissions, and be redirected back with account connected
- [ ] **Token Storage**: BOTH user token and page token stored correctly
- [ ] **User Token Expiry**: User token stored with correct expiry (~60 days from now)
- [ ] **Page Token**: Page token works for Instagram API calls
- [ ] **Token Refresh**: User tokens refresh before expiry, page tokens regenerated
- [ ] **Invalid Token Handling**: Tokens marked invalid when auth fails, user notifiable
- [ ] **Insights Collection**: Hourly job fetches and stores impression/reach/engagement data
- [ ] **Audience Data**: Daily job fetches demographic breakdowns
- [ ] **API Access**: Can query stored insights via REST API
- [ ] **Error Handling**: Failed requests logged, don't crash the system
- [ ] **Rate Limiting**: Stays under 200 requests/hour per account
- [ ] **Exponential Backoff**: 429 errors handled with backoff and retry
- [ ] **Cron Endpoints**: All 3 cron endpoints accessible via `/api/cron/*`

### Component-Level Tests

```typescript
// Test cases to implement:

// OAuth Tests
test('generates valid Facebook OAuth URL with correct scopes');
test('exchanges authorization code for short-lived token');
test('exchanges short-lived token for long-lived USER token via fb_exchange_token');
test('gets page access tokens from /me/accounts');
test('page tokens inherit long-lived status automatically');
test('discovers Instagram Business account from Facebook Page');
test('stores BOTH user token AND page token in database');
test('handles missing Instagram account gracefully');

// Token Tests
test('identifies tokens needing refresh (< 10 days to expiry)');
test('refreshes USER token via fb_exchange_token grant');
test('regenerates page token after user token refresh');
test('handles refresh failure with exponential backoff');
test('marks token as invalid after max retries');

// Insights Tests
test('fetches impressions, reach, accounts_engaged metrics');
test('uses PAGE access token for Instagram API calls');
test('stores insights with correct timestamp');
test('handles rate limit (429) with exponential backoff');
test('fetches audience demographics');

// Cron Tests
test('GET /api/cron/refresh-tokens triggers job');
test('GET /api/cron/collect-insights triggers job');
test('GET /api/cron/collect-audience triggers job');

// API Tests
test('GET /api/auth/status returns connection status');
test('GET /api/insights/:userId returns stored data');
test('GET /api/insights/:userId/audience returns demographics');
```

---

## 10. Risk Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **User token expires before refresh** | Data collection stops | Schedule refresh at 50 days (10-day buffer), run job every 6 hours |
| **Rate limit exceeded** | API calls blocked for 1 hour | Track requests per user, implement exponential backoff, batch where possible |
| **Facebook API changes** | Breaking changes to endpoints | Use versioned API (v18.0), monitor Meta changelog |
| **User revokes permissions** | Token becomes invalid | Check for auth errors on each request, mark token invalid, notify user |
| **IG account not found** | OAuth succeeds but no IG account | Clear error message to user, require Business/Creator account |
| **Database corruption** | Data loss | Regular backups, WAL mode for SQLite |
| **Vercel cold starts** | Cron jobs delayed | Use Vercel's built-in cron, acceptable for our use case |
| **Multiple IG accounts** | User has multiple pages/accounts | For MVP: use first found, future: let user select |

### Error Handling Strategy

```typescript
// Centralized error handling:

class InstagramAPIError extends Error {
  constructor(
    message: string,
    public code: number,
    public subcode?: number,
    public isRetryable: boolean = false
  ) {
    super(message);
  }
}

// Error code mapping:
const ERROR_HANDLERS: Record<number, (error: any, userId: number) => Promise<void>> = {
  190: handleInvalidToken,      // Token expired or revoked
  4: handleRateLimit,           // Rate limit hit
  10: handlePermissionError,    // Missing permission
  100: handleInvalidParam,      // Invalid parameter
};

async function handleInvalidToken(error: any, userId: number): Promise<void> {
  // Mark token as invalid in database
  await db.run(`
    UPDATE tokens
    SET is_valid = 0, invalid_reason = ?
    WHERE user_id = ?
  `, [JSON.stringify(error), userId]);

  // TODO: Queue notification to user
}

async function handleRateLimit(error: any, userId: number): Promise<void> {
  // Log and let exponential backoff handle retry
  console.log(`Rate limited for user ${userId}, will retry with backoff`);
}

async function handleAPIError(error: any, userId: number) {
  const code = error?.error?.code;
  const handler = ERROR_HANDLERS[code];

  if (handler) {
    await handler(error, userId);
  }

  await logCollection(userId, 'api_error', 'failed', JSON.stringify(error));
}
```

---

## 11. Environment Variables

```bash
# .env.example

# Facebook App Credentials (from Meta Developer Console)
FB_APP_ID=your_app_id
FB_APP_SECRET=your_app_secret

# OAuth Configuration
OAUTH_REDIRECT_URI=https://yourdomain.com/api/auth/callback
FRONTEND_SUCCESS_URL=https://yourdomain.com/?connected=true
FRONTEND_ERROR_URL=https://yourdomain.com/?error=true

# Database
DATABASE_PATH=./data/urlinsta.db

# Cron Security (optional, for Vercel)
CRON_SECRET=your_random_secret

# Optional: Logging
LOG_LEVEL=info

# Vercel (auto-set in production)
VERCEL_URL=
```

---

## 12. Frontend Implementation

### File: `public/index.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Connect Instagram</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            text-align: center;
            max-width: 400px;
        }
        h1 { margin-bottom: 10px; color: #333; }
        p { color: #666; margin-bottom: 30px; }
        .btn {
            display: inline-block;
            padding: 14px 28px;
            background: linear-gradient(45deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
            transition: transform 0.2s;
        }
        .btn:hover { transform: scale(1.05); }
        .status { margin-top: 20px; padding: 15px; border-radius: 8px; }
        .status.connected { background: #d4edda; color: #155724; }
        .status.error { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Instagram Insights</h1>
        <p>Connect your Instagram Business account to start tracking your insights.</p>

        <div id="content">
            <a href="/api/auth/login" class="btn">Connect Instagram</a>
        </div>

        <div id="status" class="status" style="display: none;"></div>
    </div>

    <script>
        // Check connection status on load
        async function checkStatus() {
            try {
                const res = await fetch('/api/auth/status');
                const data = await res.json();

                if (data.connected) {
                    document.getElementById('content').innerHTML = `
                        <p><strong>Connected as @${data.username}</strong></p>
                        <button onclick="disconnect()" class="btn" style="background: #dc3545;">Disconnect</button>
                    `;
                }
            } catch (e) {
                console.error('Status check failed:', e);
            }
        }

        // Handle URL params (success/error from OAuth)
        const params = new URLSearchParams(window.location.search);
        if (params.get('connected')) {
            const status = document.getElementById('status');
            status.className = 'status connected';
            status.textContent = 'Successfully connected!';
            status.style.display = 'block';
        } else if (params.get('error')) {
            const status = document.getElementById('status');
            status.className = 'status error';
            status.textContent = 'Connection failed. Please try again.';
            status.style.display = 'block';
        }

        checkStatus();
    </script>
</body>
</html>
```

---

## 13. Type Definitions

### File: `src/types/index.ts`

```typescript
export interface User {
  id: number;
  instagram_user_id: string;
  instagram_username: string | null;
  facebook_page_id: string | null;
  facebook_page_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface Token {
  id: number;
  user_id: number;
  user_access_token: string;      // For refresh operations
  user_token_expires_at: string;  // ~60 days from creation/refresh
  page_access_token: string;      // For Instagram API calls
  last_refreshed_at: string | null;
  is_valid: boolean;
  invalid_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface Insight {
  id: number;
  user_id: number;
  metric_name: string;
  metric_value: number;
  period: 'day' | 'week' | 'days_28' | 'lifetime';
  end_time: string | null;
  collected_at: string;
}

export interface AudienceData {
  id: number;
  user_id: number;
  demographic_type: 'city' | 'country' | 'gender_age';
  dimension_key: string;
  dimension_value: number;
  collected_at: string;
}

export interface CollectionLog {
  id: number;
  user_id: number | null;
  job_type: 'insights' | 'token_refresh' | 'audience';
  status: 'success' | 'failed' | 'skipped';
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
}

// API Response types
export interface FacebookShortLivedTokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number; // ~3600 = 1 hour
}

export interface FacebookLongLivedTokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number; // ~5184000 = 60 days
}

export interface FacebookPage {
  id: string;
  name: string;
  access_token: string; // Long-lived page token
}

export interface InstagramBusinessAccount {
  id: string;
  username?: string;
}

export interface InsightValue {
  value: number;
  end_time: string;
}

export interface InsightMetric {
  name: string;
  period: string;
  values: InsightValue[];
  title: string;
  description: string;
  id: string;
}
```

---

## 14. Vercel Configuration

### File: `vercel.json`

```json
{
  "version": 2,
  "builds": [
    {
      "src": "src/index.ts",
      "use": "@vercel/node"
    },
    {
      "src": "public/**",
      "use": "@vercel/static"
    }
  ],
  "routes": [
    {
      "src": "/api/cron/(.*)",
      "dest": "src/index.ts"
    },
    {
      "src": "/api/(.*)",
      "dest": "src/index.ts"
    },
    {
      "src": "/(.*)",
      "dest": "public/$1"
    }
  ],
  "crons": [
    {
      "path": "/api/cron/refresh-tokens",
      "schedule": "0 */6 * * *"
    },
    {
      "path": "/api/cron/collect-insights",
      "schedule": "15 * * * *"
    },
    {
      "path": "/api/cron/collect-audience",
      "schedule": "0 3 * * *"
    }
  ]
}
```

---

## Summary

This plan provides a complete implementation guide for an Instagram OAuth + Insights collection system using the **correct Facebook Login flow**. Key corrections from the previous version:

### Critical Fixes Applied

1. **OAuth Token Exchange**: Now uses `graph.facebook.com` with `fb_exchange_token` grant type (NOT `graph.instagram.com` with `ig_exchange_token`)

2. **Dual Token Storage**: Database stores BOTH:
   - **User Access Token**: For refresh operations (~60 day expiry)
   - **Page Access Token**: For Instagram API calls (never expires while user token valid)

3. **Token Refresh**: Uses correct endpoint `graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token` for user token refresh, then regenerates page token from `/me/accounts`

4. **Exponential Backoff**: Implemented for all API calls, especially for 429 rate limit errors

5. **Cron Endpoints**: Added `/api/cron/*` route handlers referenced by `vercel.json`

6. **Invalid Token Handling**: Tokens marked as invalid with reason, ready for user notification

### System Capabilities

1. **Enables easy onboarding**: Single login button for influencers
2. **Handles token lifecycle**: Automatic refresh with correct Facebook endpoints
3. **Collects comprehensive data**: Impressions, reach, engagement, follower counts, demographics
4. **Scales efficiently**: Rate limiting, batching, exponential backoff
5. **Deploys easily**: Vercel-friendly with built-in cron support

Implementation follows a phased approach, starting with core infrastructure and building up to the full data collection pipeline.
