import mongoose from 'mongoose';
import { config } from './env.js';

let isConnected = false;

export async function connectDatabase(uri?: string): Promise<boolean> {
  const targetUri = uri || config.mongodbUri;
  if (!targetUri) {
    console.warn('[Database] MONGODB_URI is not defined.');
    isConnected = false;
    return false;
  }

  if (isConnected && mongoose.connection.readyState === 1) {
    return true;
  }

  try {
    mongoose.set('strictQuery', true);
    await mongoose.connect(targetUri, {
      serverSelectionTimeoutMS: 5000,
    });
    isConnected = true;
    console.log(`[Database] Successfully connected to MongoDB at ${targetUri.replace(/\/\/[^:]+:[^@]+@/, '//***:***@')}`);
    return true;
  } catch (error: any) {
    isConnected = false;
    console.error(`[Database] Connection failed to MongoDB: ${error?.message || error}`);
    return false;
  }
}

export async function disconnectDatabase(): Promise<void> {
  if (mongoose.connection.readyState !== 0) {
    await mongoose.disconnect();
    isConnected = false;
    console.log('[Database] Disconnected from MongoDB');
  }
}

export function isDatabaseConnected(): boolean {
  return isConnected && mongoose.connection.readyState === 1;
}
