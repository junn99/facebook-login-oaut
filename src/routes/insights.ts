import { Router } from 'express';
import { db } from '../db/connection';

const router = Router();

// GET /api/insights/:userId - Get insights for a user
router.get('/:userId', (req, res) => {
  const { userId } = req.params;
  const { metric, days = 7 } = req.query;

  let query = `
    SELECT * FROM insights
    WHERE user_id = ?
    AND collected_at > datetime('now', '-${parseInt(days as string)} days')
  `;
  const params: any[] = [userId];

  if (metric) {
    query += ' AND metric_name = ?';
    params.push(metric);
  }

  query += ' ORDER BY collected_at DESC';

  const insights = db.prepare(query).all(...params);
  res.json({ insights });
});

// GET /api/insights/:userId/audience - Get audience data
router.get('/:userId/audience', (req, res) => {
  const { userId } = req.params;

  const audience = db.prepare(`
    SELECT * FROM audience_data
    WHERE user_id = ?
    ORDER BY collected_at DESC
    LIMIT 3
  `).all(userId);

  res.json({ audience });
});

// GET /api/insights/:userId/summary - Get latest metrics summary
router.get('/:userId/summary', (req, res) => {
  const { userId } = req.params;

  const summary = db.prepare(`
    SELECT metric_name, metric_value, collected_at
    FROM insights
    WHERE user_id = ?
    AND id IN (
      SELECT MAX(id) FROM insights WHERE user_id = ? GROUP BY metric_name
    )
  `).all(userId, userId);

  res.json({ summary });
});

export default router;
