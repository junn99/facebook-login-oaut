/**
 * Database Models
 */

export interface User {
  id: number;
  instagram_account_id: string;
  instagram_username: string | null;
  facebook_page_id: string | null;
  created_at: string;
  updated_at: string;
}

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

export interface Insight {
  id: number;
  token_id: number;
  metric_name: string;
  metric_value: number;
  period: string;
  end_time: Date;
  created_at: Date;
}

export interface AudienceData {
  id: number;
  token_id: number;
  metric_name: string;
  metric_data: Record<string, any>;
  collected_at: Date;
  created_at: Date;
}

export interface CollectionLog {
  id: number;
  token_id: number;
  collection_type: string;
  status: 'success' | 'failure';
  error_message?: string;
  metrics_collected?: number;
  created_at: Date;
}

/**
 * Facebook/Instagram API Response Types
 */

export interface FacebookTokenResponse {
  access_token: string;
  token_type: string;
  expires_in?: number;
}

export interface LongLivedTokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface PageAccountResponse {
  data: Array<{
    id: string;
    name: string;
    access_token: string;
    category?: string;
    tasks?: string[];
  }>;
  paging?: {
    cursors?: {
      before: string;
      after: string;
    };
  };
}

export interface InstagramBusinessAccount {
  id: string;
  username: string;
  name?: string;
  profile_picture_url?: string;
  followers_count?: number;
  follows_count?: number;
  media_count?: number;
  biography?: string;
  website?: string;
}

/**
 * Instagram Insights Response Types
 */

export interface InsightMetric {
  name: string;
  period: 'day' | 'week' | 'days_28' | 'lifetime';
  values: Array<{
    value: number | Record<string, any>;
    end_time: string;
  }>;
  title?: string;
  description?: string;
  id?: string;
}

export interface InsightsResponse {
  data: InsightMetric[];
  paging?: {
    previous?: string;
    next?: string;
  };
}

/**
 * Rate Limiting
 */

export interface RateLimitInfo {
  remaining: number;
  reset_at: Date;
  limit?: number;
  used?: number;
}

/**
 * OAuth Flow
 */

export interface OAuthState {
  state: string;
  created_at: Date;
  expires_at: Date;
  user_id?: number;
}

/**
 * Error Response Types
 */

export interface FacebookErrorResponse {
  error: {
    message: string;
    type: string;
    code: number;
    error_subcode?: number;
    fbtrace_id: string;
  };
}

/**
 * Application Configuration
 */

export interface AppConfig {
  facebook: {
    app_id: string;
    app_secret: string;
    redirect_uri: string;
  };
  database: {
    url: string;
  };
  server: {
    port: number;
    host: string;
  };
}
