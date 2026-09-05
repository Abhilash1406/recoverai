import { createApp } from './app.js';
import { config } from './config/env.js';

const app = createApp();

const server = app.listen(config.port, () => {
  console.log(
    JSON.stringify({
      level: 'INFO',
      timestamp: new Date().toISOString(),
      message: `RecoverAI API listening`,
      port: config.port,
      environment: config.nodeEnv,
      health: `http://localhost:${config.port}/api/v1/health`,
    }),
  );
});

// Graceful shutdown — important for later phases with DB connections
process.on('SIGTERM', () => {
  console.log(JSON.stringify({ level: 'INFO', message: 'SIGTERM received, shutting down gracefully' }));
  server.close(() => {
    console.log(JSON.stringify({ level: 'INFO', message: 'Server closed' }));
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  console.log(JSON.stringify({ level: 'INFO', message: 'SIGINT received, shutting down gracefully' }));
  server.close(() => {
    console.log(JSON.stringify({ level: 'INFO', message: 'Server closed' }));
    process.exit(0);
  });
});
