// worker/src/index.js
import { startFetchWorker, startAnalysisWorker, startVerifyWorker } from './workers.js';
import { articleFetchQueue, articleAnalysisQueue, articleVerifyQueue } from './queues.js';

console.log('Climate Intelligence Worker starting...');
console.log(`Redis: ${process.env.REDIS_HOST || 'redis'}:${process.env.REDIS_PORT || '6379'}`);

const fetchWorker = startFetchWorker();
const analysisWorker = startAnalysisWorker();
const verifyWorker = startVerifyWorker();

console.log('Workers started:');
console.log('  article-fetch    (concurrency: 5)');
console.log('  article-analysis (concurrency: 1)');
console.log('  article-verify   (concurrency: 3)');

let isShuttingDown = false;

async function shutdown() {
  if (isShuttingDown) return;
  isShuttingDown = true;
  console.log('Shutting down workers...');
  await Promise.all([fetchWorker.close(), analysisWorker.close(), verifyWorker.close()]);
  await Promise.all([articleFetchQueue.close(), articleAnalysisQueue.close(), articleVerifyQueue.close()]);
  console.log('Workers stopped cleanly');
  process.exit(0);
}

process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);
