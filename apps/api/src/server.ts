import { createApp } from './app.js';
import { config } from './config/env.js';
import { connectDatabase, disconnectDatabase } from './config/database.js';

async function startServer() {
  if (config.persistenceMode === 'mongodb') {
    const success = await connectDatabase();
    if (!success) {
      console.error(
        JSON.stringify({
          level: 'ERROR',
          timestamp: new Date().toISOString(),
          message: `Failed to connect to MongoDB in mongodb mode. Service will start but DB operations may fail.`,
        }),
      );
    }
  }

  const app = createApp();

  const server = app.listen(config.port, () => {
    console.log(
      JSON.stringify({
        level: 'INFO',
        timestamp: new Date().toISOString(),
        message: `RecoverAI API listening`,
        port: config.port,
        environment: config.nodeEnv,
        persistenceMode: config.persistenceMode,
        health: `http://localhost:${config.port}/api/v1/health`,
      }),
    );
  });

  const shutdown = async (signal: string) => {
    console.log(JSON.stringify({ level: 'INFO', message: `${signal} received, shutting down gracefully` }));
    await disconnectDatabase();
    server.close(() => {
      console.log(JSON.stringify({ level: 'INFO', message: 'Server closed' }));
      process.exit(0);
    });
  };

  process.on('SIGTERM', () => shutdown('SIGTERM'));
  process.on('SIGINT', () => shutdown('SIGINT'));
}

startServer().catch((err) => {
  console.error('[Server Startup Error]', err);
});
