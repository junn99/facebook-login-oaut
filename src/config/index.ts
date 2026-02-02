import dotenv from 'dotenv';

dotenv.config();

export const config = {
  facebook: {
    appId: process.env.FB_APP_ID || '',
    appSecret: process.env.FB_APP_SECRET || '',
    redirectUri: process.env.OAUTH_REDIRECT_URI || 'http://localhost:3000/auth/facebook/callback',
  },
  frontend: {
    successUrl: process.env.FRONTEND_SUCCESS_URL || 'http://localhost:5173/success',
    errorUrl: process.env.FRONTEND_ERROR_URL || 'http://localhost:5173/error',
  },
  database: {
    path: process.env.DATABASE_PATH || './data/urlinsta.db',
  },
  cron: {
    secret: process.env.CRON_SECRET || '',
  },
  server: {
    port: parseInt(process.env.PORT || '3000', 10),
  },
};
