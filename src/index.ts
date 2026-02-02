import express from 'express';
import path from 'path';
import { config } from './config';
import healthRoutes from './routes/health';
import authRoutes from './routes/auth';
import insightsRoutes from './routes/insights';
import cronRoutes from './routes/cron';

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

app.listen(config.port, () => {
  console.log(`Server running on port ${config.port}`);
});

export default app;
