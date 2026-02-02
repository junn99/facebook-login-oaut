import express from 'express';
import path from 'path';
import { config } from '../src/config';
import healthRoutes from '../src/routes/health';
import authRoutes from '../src/routes/auth';
import insightsRoutes from '../src/routes/insights';
import cronRoutes from '../src/routes/cron';

const app = express();

app.use(express.json());
app.use(express.static(path.join(__dirname, '../public')));

// Routes
app.use('/api/health', healthRoutes);
app.use('/api/auth', authRoutes);
app.use('/api/insights', insightsRoutes);
app.use('/api/cron', cronRoutes);

// Serve frontend
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, '../public/index.html'));
});

export default app;
