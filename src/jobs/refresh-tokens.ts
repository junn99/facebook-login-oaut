import { refreshAllExpiringTokens } from '../services/token';

export async function runTokenRefreshJob(): Promise<{ refreshed: number; failed: number }> {
  console.log('Starting token refresh job...');
  const result = await refreshAllExpiringTokens();
  console.log(`Token refresh complete: ${result.refreshed} refreshed, ${result.failed} failed`);
  return result;
}
