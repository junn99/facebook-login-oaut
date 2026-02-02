import { Router } from 'express';
import crypto from 'crypto';
import { config } from '../config';
import * as oauth from '../services/oauth';
import { createUser, getUser, saveToken } from '../db/connection';

const router = Router();

// Store CSRF states temporarily (in production, use Redis)
const pendingStates = new Map<string, { createdAt: number }>();

// GET /api/auth/login - Redirect to Facebook OAuth
router.get('/login', (req, res) => {
  const state = crypto.randomBytes(16).toString('hex');
  pendingStates.set(state, { createdAt: Date.now() });

  // Clean old states (older than 10 minutes)
  const tenMinutesAgo = Date.now() - 10 * 60 * 1000;
  for (const [key, value] of pendingStates) {
    if (value.createdAt < tenMinutesAgo) pendingStates.delete(key);
  }

  const authUrl = oauth.generateAuthUrl(state);
  res.redirect(authUrl);
});

// GET /api/auth/callback - Handle OAuth callback
router.get('/callback', async (req, res) => {
  try {
    const { code, state, error } = req.query;

    if (error) {
      return res.redirect(`${config.frontendErrorUrl}&reason=${error}`);
    }

    // Validate CSRF state
    if (!state || !pendingStates.has(state as string)) {
      return res.redirect(`${config.frontendErrorUrl}&reason=invalid_state`);
    }
    pendingStates.delete(state as string);

    // Exchange code for tokens (full flow)
    const shortToken = await oauth.exchangeCodeForToken(code as string);
    const { token: longToken, expiresIn } = await oauth.exchangeForLongLivedToken(shortToken);
    const { pageId, pageToken } = await oauth.getPageAccessToken(longToken);
    const { igAccountId, username } = await oauth.getInstagramBusinessAccount(pageId, pageToken);

    // Create or update user
    let user = await getUser(igAccountId);
    if (!user) {
      user = await createUser(igAccountId, username, pageId);
    }

    // Save tokens
    const expiresAt = new Date(Date.now() + expiresIn * 1000);
    await saveToken(user.id, longToken, pageToken, expiresAt);

    res.redirect(config.frontendSuccessUrl);
  } catch (err) {
    console.error('OAuth callback error:', err);
    res.redirect(`${config.frontendErrorUrl}&reason=auth_failed`);
  }
});

export default router;
