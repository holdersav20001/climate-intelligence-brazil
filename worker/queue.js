import { Queue } from 'bullmq';

const connection = { host: 'redis', port: 6379 };

const agentQueue = new Queue('agent-heartbeats', { connection });

console.log('Worker ready — connected to Redis, no jobs queued yet');

// Keep process alive
process.on('SIGTERM', async () => {
  await agentQueue.close();
  process.exit(0);
});
