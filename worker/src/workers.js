// worker/src/workers.js
import { Worker } from 'bullmq';
import { enqueueAnalysis, enqueueVerify } from './queues.js';

const redisConnection = {
  host: process.env.REDIS_HOST || 'redis',
  port: parseInt(process.env.REDIS_PORT || '6379'),
};

export function startFetchWorker() {
  const worker = new Worker(
    'article-fetch',
    async (job) => {
      const { url, metadata } = job.data;
      console.log(`[fetch] Processing: ${url}`);

      const articleId = metadata.articleId || null;

      if (articleId) {
        const analysisJobId = await enqueueAnalysis(articleId, url, metadata.scoutRunId);
        console.log(`[fetch] Enqueued analysis job ${analysisJobId} for article ${articleId}`);
      } else {
        console.log(`[fetch] No articleId in metadata — article not yet in DB, skipping analysis enqueue`);
      }

      return { url, articleId, processedAt: new Date().toISOString() };
    },
    {
      connection: redisConnection,
      concurrency: 5,
    }
  );

  worker.on('completed', (job) => {
    console.log(`[fetch] Job ${job.id} completed`);
  });

  worker.on('failed', (job, err) => {
    console.error(`[fetch] Job ${job?.id} failed: ${err.message}`);
  });

  return worker;
}

export function startAnalysisWorker() {
  const worker = new Worker(
    'article-analysis',
    async (job) => {
      const { articleId, url, scoutRunId } = job.data;
      console.log(`[analysis] Processing article ${articleId}: ${url}`);

      const analystRunId = `worker-${Date.now()}`;
      const verifyJobId = await enqueueVerify(articleId, url, analystRunId);
      console.log(`[analysis] Enqueued verify job ${verifyJobId} for article ${articleId}`);

      return { articleId, url, analystRunId, processedAt: new Date().toISOString() };
    },
    {
      connection: redisConnection,
      concurrency: 1, // CRITICAL: only one Analyst at a time
    }
  );

  worker.on('completed', (job) => {
    console.log(`[analysis] Job ${job.id} completed`);
  });

  worker.on('failed', (job, err) => {
    console.error(`[analysis] Job ${job?.id} failed: ${err.message}`);
  });

  return worker;
}

export function startVerifyWorker() {
  const worker = new Worker(
    'article-verify',
    async (job) => {
      const { articleId, url, analystRunId } = job.data;
      console.log(`[verify] Processing article ${articleId}: ${url}`);

      return { articleId, url, verifiedAt: new Date().toISOString() };
    },
    {
      connection: redisConnection,
      concurrency: 3,
    }
  );

  worker.on('completed', (job) => {
    console.log(`[verify] Job ${job.id} completed`);
  });

  worker.on('failed', (job, err) => {
    console.error(`[verify] Job ${job?.id} failed: ${err.message}`);
  });

  return worker;
}
