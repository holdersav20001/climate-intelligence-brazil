// worker/src/queues.js
import { Queue } from 'bullmq';

const redisConnection = {
  host: process.env.REDIS_HOST || 'redis',
  port: parseInt(process.env.REDIS_PORT || '6379'),
};

export const articleFetchQueue = new Queue('article-fetch', {
  connection: redisConnection,
  defaultJobOptions: {
    attempts: 3,
    backoff: { type: 'exponential', delay: 5000 },
    removeOnComplete: { count: 500 },
    removeOnFail: { count: 200 },
  },
});

export const articleAnalysisQueue = new Queue('article-analysis', {
  connection: redisConnection,
  defaultJobOptions: {
    attempts: 2,
    backoff: { type: 'fixed', delay: 10000 },
    removeOnComplete: { count: 500 },
    removeOnFail: { count: 200 },
  },
});

export const articleVerifyQueue = new Queue('article-verify', {
  connection: redisConnection,
  defaultJobOptions: {
    attempts: 2,
    backoff: { type: 'fixed', delay: 5000 },
    removeOnComplete: { count: 500 },
    removeOnFail: { count: 200 },
  },
});

export async function enqueueFetch(url, metadata = {}) {
  const job = await articleFetchQueue.add(
    'fetch',
    { url, metadata, enqueuedAt: new Date().toISOString() },
    { jobId: `fetch:${Buffer.from(url).toString('base64url').slice(0, 40)}` }
  );
  return job.id;
}

export async function enqueueAnalysis(articleId, url, scoutRunId) {
  const job = await articleAnalysisQueue.add(
    'analyse',
    { articleId, url, scoutRunId, enqueuedAt: new Date().toISOString() }
  );
  return job.id;
}

export async function enqueueVerify(articleId, url, analystRunId) {
  const job = await articleVerifyQueue.add(
    'verify',
    { articleId, url, analystRunId, enqueuedAt: new Date().toISOString() }
  );
  return job.id;
}
