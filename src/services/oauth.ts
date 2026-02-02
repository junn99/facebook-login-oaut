import axios from 'axios';
import { config } from '../config';

const FACEBOOK_GRAPH_API = 'https://graph.facebook.com/v18.0';
const FACEBOOK_OAUTH_URL = 'https://www.facebook.com/v18.0/dialog/oauth';

interface LongLivedTokenResponse {
  token: string;
  expiresIn: number;
}

interface PageAccessTokenResponse {
  pageId: string;
  pageToken: string;
}

interface InstagramBusinessAccountResponse {
  igAccountId: string;
  username: string;
}

/**
 * Generate Facebook OAuth authorization URL
 * @param state - Random state string for CSRF protection
 * @returns Authorization URL for Facebook Login
 */
export function generateAuthUrl(state: string): string {
  const params = new URLSearchParams({
    client_id: config.fbAppId,
    redirect_uri: config.oauthRedirectUri,
    state,
    scope: 'instagram_basic,instagram_manage_insights,pages_show_list,pages_read_engagement',
  });

  return `${FACEBOOK_OAUTH_URL}?${params.toString()}`;
}

/**
 * Exchange authorization code for short-lived user access token
 * @param code - Authorization code from Facebook callback
 * @returns Short-lived user access token
 */
export async function exchangeCodeForToken(code: string): Promise<string> {
  try {
    const response = await axios.get(`${FACEBOOK_GRAPH_API}/oauth/access_token`, {
      params: {
        client_id: config.fbAppId,
        client_secret: config.fbAppSecret,
        redirect_uri: config.oauthRedirectUri,
        code,
      },
    });

    if (!response.data.access_token) {
      throw new Error('No access token in response');
    }

    return response.data.access_token;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(`Failed to exchange code for token: ${error.response?.data?.error?.message || error.message}`);
    }
    throw error;
  }
}

/**
 * Exchange short-lived token for long-lived token (~60 days)
 * @param shortToken - Short-lived user access token
 * @returns Object containing long-lived token and expiration time in seconds
 */
export async function exchangeForLongLivedToken(shortToken: string): Promise<LongLivedTokenResponse> {
  try {
    const response = await axios.get(`${FACEBOOK_GRAPH_API}/oauth/access_token`, {
      params: {
        grant_type: 'fb_exchange_token',
        client_id: config.fbAppId,
        client_secret: config.fbAppSecret,
        fb_exchange_token: shortToken,
      },
    });

    if (!response.data.access_token) {
      throw new Error('No access token in response');
    }

    return {
      token: response.data.access_token,
      expiresIn: response.data.expires_in || 5184000, // Default 60 days
    };
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(`Failed to exchange for long-lived token: ${error.response?.data?.error?.message || error.message}`);
    }
    throw error;
  }
}

/**
 * Get Facebook Page access token from user token
 * @param userToken - Long-lived user access token
 * @returns Object containing page ID and page access token
 */
export async function getPageAccessToken(userToken: string): Promise<PageAccessTokenResponse> {
  try {
    const response = await axios.get(`${FACEBOOK_GRAPH_API}/me/accounts`, {
      params: {
        access_token: userToken,
      },
    });

    if (!response.data.data || response.data.data.length === 0) {
      throw new Error('No Facebook Pages found for this account');
    }

    const firstPage = response.data.data[0];

    return {
      pageId: firstPage.id,
      pageToken: firstPage.access_token,
    };
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(`Failed to get page access token: ${error.response?.data?.error?.message || error.message}`);
    }
    throw error;
  }
}

/**
 * Get Instagram Business Account ID and username from Facebook Page
 * @param pageId - Facebook Page ID
 * @param pageToken - Facebook Page access token
 * @returns Object containing Instagram Business Account ID and username
 */
export async function getInstagramBusinessAccount(
  pageId: string,
  pageToken: string
): Promise<InstagramBusinessAccountResponse> {
  try {
    const response = await axios.get(`${FACEBOOK_GRAPH_API}/${pageId}`, {
      params: {
        fields: 'instagram_business_account{id,username}',
        access_token: pageToken,
      },
    });

    if (!response.data.instagram_business_account) {
      throw new Error('No Instagram Business Account linked to this Facebook Page');
    }

    const igAccount = response.data.instagram_business_account;

    return {
      igAccountId: igAccount.id,
      username: igAccount.username,
    };
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(`Failed to get Instagram Business Account: ${error.response?.data?.error?.message || error.message}`);
    }
    throw error;
  }
}
