import { Router } from 'express';
import { config } from '../config';
import { runTokenRefreshJob } from '../jobs/refresh-tokens';
import { runInsightsCollectionJob } from '../jobs/collect-insights';

const router = Router();

// Middleware to verify cron secret
const verifyCronSecret = (req: any, res: any, next: any) => {
  const authHeader = req.headers.authorization;
  if (authHeader !== `Bearer ${config.cronSecret}`) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  next();
};

router.use(verifyCronSecret);

// POST /api/cron/refresh-tokens - Run every 6 hours
router.post('/refresh-tokens', async (req, res) => {
  try {
    const result = await runTokenRefreshJob();
    res.json({ ...result, success: true });
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// POST /api/cron/collect-insights - Run every hour
router.post('/collect-insights', async (req, res) => {
  try {
    const result = await runInsightsCollectionJob(false);
    res.json({ ...result, success: true });
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// POST /api/cron/collect-audience - Run daily
router.post('/collect-audience', async (req, res) => {
  try {
    const result = await runInsightsCollectionJob(true);
    res.json({ ...result, success: true });
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
});

export default router;
