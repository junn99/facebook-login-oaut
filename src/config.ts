import dotenv from 'dotenv';
dotenv.config();

export const config = {
  fbAppId: process.env.FB_APP_ID!,
  fbAppSecret: process.env.FB_APP_SECRET!,
  oauthRedirectUri: process.env.OAUTH_REDIRECT_URI!,
  frontendSuccessUrl: process.env.FRONTEND_SUCCESS_URL!,
  frontendErrorUrl: process.env.FRONTEND_ERROR_URL!,
  databasePath: process.env.DATABASE_PATH || './data/urlinsta.db',
  cronSecret: process.env.CRON_SECRET!,
  port: parseInt(process.env.PORT || '3000', 10),
  graphApiVersion: 'v18.0',
  graphApiBase: 'https://graph.facebook.com',
};
