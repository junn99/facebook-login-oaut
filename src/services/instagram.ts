import axios, { AxiosError } from 'axios';
import { config } from '../config';

/**
 * Custom error for rate limiting
 */
export class RateLimitError extends Error {
  constructor(message: string, public retryAfter?: number) {
    super(message);
    this.name = 'RateLimitError';
  }
}

/**
 * Rate limiter to track requests per Instagram account
 * Enforces 180 requests per hour per account (safety margin under 200)
 */
export class RateLimiter {
  private requests: Map<string, number[]> = new Map();
  private readonly RATE_LIMIT = 180;
  private readonly WINDOW_MS = 60 * 60 * 1000; // 1 hour in milliseconds

  /**
   * Check if a request can be made for the given Instagram account
   */
  canMakeRequest(igAccountId: string): boolean {
    this.cleanExpiredRequests(igAccountId);
    const accountRequests = this.requests.get(igAccountId) || [];
    return accountRequests.length < this.RATE_LIMIT;
  }

  /**
   * Record a request for the given Instagram account
   */
  recordRequest(igAccountId: string): void {
    this.cleanExpiredRequests(igAccountId);
    const accountRequests = this.requests.get(igAccountId) || [];
    accountRequests.push(Date.now());
    this.requests.set(igAccountId, accountRequests);
  }

  /**
   * Get remaining requests for the given Instagram account
   */
  getRemainingRequests(igAccountId: string): number {
    this.cleanExpiredRequests(igAccountId);
    const accountRequests = this.requests.get(igAccountId) || [];
    return Math.max(0, this.RATE_LIMIT - accountRequests.length);
  }

  /**
   * Clean up expired requests outside the time window
   */
  private cleanExpiredRequests(igAccountId: string): void {
    const now = Date.now();
    const accountRequests = this.requests.get(igAccountId) || [];
    const validRequests = accountRequests.filter(
      (timestamp) => now - timestamp < this.WINDOW_MS
    );
    this.requests.set(igAccountId, validRequests);
  }
}

/**
 * Global rate limiter instance
 */
export const rateLimiter = new RateLimiter();

/**
 * Sleep helper for delays
 */
const sleep = (ms: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Generate random jitter between 0 and 1000ms
 */
const getJitter = (): number => Math.random() * 1000;

/**
 * Exponential backoff helper with jitter
 * Base delay: 1 second
 * Max retries: 5
 * Formula: baseDelay * 2^attempt + jitter
 */
async function withExponentialBackoff<T>(
  fn: () => Promise<T>,
  maxRetries = 5,
  baseDelay = 1000
): Promise<T> {
  let lastError: Error | undefined;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;

      // Don't retry on final attempt
      if (attempt === maxRetries) {
        break;
      }

      // Check if it's a rate limit error
      if (error instanceof RateLimitError) {
        const delay = error.retryAfter
          ? error.retryAfter * 1000
          : baseDelay * Math.pow(2, attempt) + getJitter();
        console.warn(
          `Rate limit hit, retrying in ${Math.round(delay)}ms (attempt ${attempt + 1}/${maxRetries})`
        );
        await sleep(delay);
        continue;
      }

      // Check if it's an axios error with 429 status
      if (axios.isAxiosError(error) && error.response?.status === 429) {
        const retryAfter = error.response.headers['retry-after'];
        const delay = retryAfter
          ? parseInt(retryAfter, 10) * 1000
          : baseDelay * Math.pow(2, attempt) + getJitter();
        console.warn(
          `HTTP 429 received, retrying in ${Math.round(delay)}ms (attempt ${attempt + 1}/${maxRetries})`
        );
        await sleep(delay);
        continue;
      }

      // For other errors, apply exponential backoff
      if (axios.isAxiosError(error) && error.response && error.response.status >= 500) {
        const delay = baseDelay * Math.pow(2, attempt) + getJitter();
        console.warn(
          `Server error (${error.response.status}), retrying in ${Math.round(delay)}ms (attempt ${attempt + 1}/${maxRetries})`
        );
        await sleep(delay);
        continue;
      }

      // Don't retry other errors
      throw error;
    }
  }

  throw lastError;
}

/**
 * Fetch insights for an Instagram account
 * Metrics: impressions, reach, accounts_engaged, follower_count
 * Period: day, week, days_28
 */
export async function fetchInsights(
  igAccountId: string,
  pageToken?: string,
  metrics: string[] = ['impressions', 'reach', 'accounts_engaged', 'follower_count'],
  period: 'day' | 'week' | 'days_28' = 'day'
): Promise<any> {
  // Check rate limit before making request
  if (!rateLimiter.canMakeRequest(igAccountId)) {
    throw new RateLimitError(
      `Rate limit exceeded for account ${igAccountId}. Remaining: ${rateLimiter.getRemainingRequests(igAccountId)}`
    );
  }

  return withExponentialBackoff(async () => {
    try {
      const params: any = {
        metric: metrics.join(','),
        period,
        access_token: pageToken,
      };

      const response = await axios.get(
        `${config.graphApiBase}/${config.graphApiVersion}/${igAccountId}/insights`,
        { params }
      );

      // Record successful request
      rateLimiter.recordRequest(igAccountId);

      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError;
        if (axiosError.response?.status === 429) {
          const retryAfter = axiosError.response.headers['retry-after'];
          throw new RateLimitError(
            'Instagram API rate limit exceeded',
            retryAfter ? parseInt(retryAfter, 10) : undefined
          );
        }
      }
      throw error;
    }
  });
}

/**
 * Fetch audience data for an Instagram account
 * Metrics: audience_city, audience_country, audience_gender_age
 * Period: lifetime
 */
export async function fetchAudienceData(
  igAccountId: string,
  pageToken?: string
): Promise<any> {
  // Check rate limit before making request
  if (!rateLimiter.canMakeRequest(igAccountId)) {
    throw new RateLimitError(
      `Rate limit exceeded for account ${igAccountId}. Remaining: ${rateLimiter.getRemainingRequests(igAccountId)}`
    );
  }

  return withExponentialBackoff(async () => {
    try {
      const params: any = {
        metric: 'audience_city,audience_country,audience_gender_age',
        period: 'lifetime',
        access_token: pageToken,
      };

      const response = await axios.get(
        `${config.graphApiBase}/${config.graphApiVersion}/${igAccountId}/insights`,
        { params }
      );

      // Record successful request
      rateLimiter.recordRequest(igAccountId);

      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError;
        if (axiosError.response?.status === 429) {
          const retryAfter = axiosError.response.headers['retry-after'];
          throw new RateLimitError(
            'Instagram API rate limit exceeded',
            retryAfter ? parseInt(retryAfter, 10) : undefined
          );
        }
      }
      throw error;
    }
  });
}
