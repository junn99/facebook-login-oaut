import { Router } from 'express';
import { db } from '../db/connection';

const router = Router();

// GET /api/insights/:userId - Get insights for a user
router.get('/:userId', async (req, res) => {
  try {
    const { userId } = req.params;
    const { metric, days = 7 } = req.query;

    const daysNum = parseInt(days as string);
    let sql = `
      SELECT * FROM insights
      WHERE user_id = ?
      AND collected_at > datetime('now', '-${daysNum} days')
    `;
    const args: any[] = [userId];

    if (metric) {
      sql += ' AND metric_name = ?';
      args.push(metric);
    }

    sql += ' ORDER BY collected_at DESC';

    const result = await db.execute({ sql, args });
    res.json({ insights: result.rows });
  } catch (error) {
    console.error('Error fetching insights:', error);
    res.status(500).json({ error: 'Failed to fetch insights' });
  }
});

// GET /api/insights/:userId/audience - Get audience data
router.get('/:userId/audience', async (req, res) => {
  try {
    const { userId } = req.params;

    const result = await db.execute({
      sql: `SELECT * FROM audience_data
            WHERE user_id = ?
            ORDER BY collected_at DESC
            LIMIT 3`,
      args: [userId],
    });

    res.json({ audience: result.rows });
  } catch (error) {
    console.error('Error fetching audience data:', error);
    res.status(500).json({ error: 'Failed to fetch audience data' });
  }
});

// GET /api/insights/:userId/summary - Get latest metrics summary
router.get('/:userId/summary', async (req, res) => {
  try {
    const { userId } = req.params;

    const result = await db.execute({
      sql: `SELECT metric_name, metric_value, collected_at
            FROM insights
            WHERE user_id = ?
            AND id IN (
              SELECT MAX(id) FROM insights WHERE user_id = ? GROUP BY metric_name
            )`,
      args: [userId, userId],
    });

    res.json({ summary: result.rows });
  } catch (error) {
    console.error('Error fetching summary:', error);
    res.status(500).json({ error: 'Failed to fetch summary' });
  }
});

export default router;
