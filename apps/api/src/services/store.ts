import { config } from '../config/env.js';
import { IDataStore } from './store/IDataStore.js';
import { InMemoryDataStore } from './store/InMemoryDataStore.js';
import { MongoDataStore } from './store/MongoDataStore.js';

export * from './store/IDataStore.js';
export { InMemoryDataStore } from './store/InMemoryDataStore.js';
export { MongoDataStore } from './store/MongoDataStore.js';

export function getDataStore(): IDataStore {
  if (config.persistenceMode === 'mongodb') {
    return MongoDataStore.getInstance();
  }
  return InMemoryDataStore.getInstance();
}

export const dataStore: IDataStore = getDataStore();
