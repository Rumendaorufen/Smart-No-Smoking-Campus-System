import axios from 'axios';

const LOG_API = '/api/logs';
const MAX_CACHE = 20;

interface LogEntry {
  level: string;
  message: string;
  endpoint: string;
  traceId: string;
  userId?: string;
  metadata?: Record<string, unknown>;
}

class LogCollector {
  private cache: LogEntry[] = [];
  private submitting = false;
  private sessionTraceId = '';

  constructor() {
    this.sessionTraceId = this.generateTraceId();
  }

  /** Generate a unique trace ID */
  generateTraceId(): string {
    return crypto.randomUUID().replace(/-/g, '');
  }

  /** Get the session trace ID */
  getTraceId(): string {
    return this.sessionTraceId;
  }

  /** Report an error or warning to the backend */
  report(level: 'ERROR' | 'WARNING', message: string, endpoint = '', metadata?: Record<string, unknown>): void {
    const entry: LogEntry = {
      level,
      message: message.slice(0, 1000),
      endpoint: endpoint || window.location.pathname,
      traceId: this.sessionTraceId,
    };
    if (metadata) entry.metadata = metadata;

    this.cache.push(entry);
    if (this.cache.length >= MAX_CACHE) {
      this.flush();
    } else {
      this.scheduleFlush();
    }
  }

  private scheduleFlush(): void {
    setTimeout(() => this.flush(), 3000);
  }

  async flush(): Promise<void> {
    if (this.submitting || this.cache.length === 0) return;
    this.submitting = true;
    const batch = this.cache.splice(0, MAX_CACHE);
    try {
      await axios.post(LOG_API, batch.length === 1 ? batch[0] : batch, { timeout: 5000 });
    } catch {
      this.cache.unshift(...batch);
      if (this.cache.length > MAX_CACHE) this.cache.length = MAX_CACHE;
    } finally {
      this.submitting = false;
    }
  }
}

export const logCollector = new LogCollector();
export default logCollector;
