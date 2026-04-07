// worker/queue.js
// Re-exports from src/queues.js for backward compatibility.
// New code should import from worker/src/queues.js directly.
export { enqueueFetch, enqueueAnalysis, enqueueVerify } from './src/queues.js';
