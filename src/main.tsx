import { StrictMode } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { ErrorBoundary } from './components/ErrorBoundary';
import App from './App.tsx';
import './index.css';
import { envDiagnostics, envAllRequiredPresent } from './lib/env';

// ── Diagnostics ───────────────────────────────────────────────
const DIAG = {
  env: envDiagnostics,
  envOk: envAllRequiredPresent,
  ua: navigator.userAgent,
  ts: new Date().toISOString(),
};

function logFatal(stage: string, err: unknown) {
  console.error(`[SmartPip ${stage}]`, err);
}

// ── Global error handlers ─────────────────────────────────────
// Catch errors that escape React's render tree (async callbacks,
// setTimeout, native event listeners, etc.)
window.onerror = (message, source, lineno, colno, error) => {
  logFatal('window.onerror', { message, source, lineno, colno, error });
  showInlineFallback(error);
};

window.addEventListener('unhandledrejection', (e) => {
  logFatal('unhandledrejection', e.reason);
});

// ── Inline fallback renderer ──────────────────────────────────
// If everything else fails, inject a visible diagnostic screen
// directly into the DOM so the user never sees a blank page.
function showInlineFallback(err?: unknown) {
  const root = document.getElementById('root');
  if (!root || root.dataset.fallback === '1') return;
  root.dataset.fallback = '1';

  const msg = err instanceof Error ? err.message : String(err ?? 'Unknown error');
  const stack = err instanceof Error ? err.stack : '';
  root.innerHTML = `
    <div style="min-height:100vh;display:flex;align-items:center;justify-content:center;background:#0a0a14;color:#e2e8f0;font-family:Inter,system-ui,sans-serif;padding:2rem">
      <div style="max-width:480px;width:100%;text-align:center">
        <div style="width:48px;height:48px;margin:0 auto 1rem;border-radius:12px;background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.2);display:flex;align-items:center;justify-content:center;font-size:1.25rem;color:#f87171">!</div>
        <h1 style="font-size:1.125rem;font-weight:600;margin-bottom:.5rem">SmartPip failed to start</h1>
        <p style="font-size:.8125rem;color:#94a3b8;line-height:1.6;margin-bottom:1.25rem">
          The application encountered a fatal error during startup. This is usually caused by a missing environment variable, a network issue, or a browser compatibility problem.
        </p>
        <div style="background:#12121a;border:1px solid #1e293b;border-radius:8px;padding:.75rem 1rem;margin-bottom:1.25rem;text-align:left">
          <p style="font-size:.75rem;color:#64748b;margin-bottom:.375rem">Error</p>
          <pre style="font-family:JetBrains Mono,monospace;font-size:.6875rem;color:#f87171;white-space:pre-wrap;word-break:break-all;margin:0;max-height:120px;overflow:auto">${msg}${stack ? '\n\n' + stack : ''}</pre>
        </div>
        <div style="display:flex;gap:.5rem;justify-content:center;flex-wrap:wrap">
          <button onclick="window.location.reload()" style="padding:.5rem 1rem;border-radius:8px;background:rgba(59,130,246,.2);color:#60a5fa;border:none;font-size:.8125rem;font-weight:500;cursor:pointer">Reload page</button>
          <button onclick="navigator.clipboard?.writeText(document.querySelector('pre')?.textContent||'')" style="padding:.5rem 1rem;border-radius:8px;background:rgba(148,163,184,.1);color:#94a3b8;border:1px solid #1e293b;font-size:.8125rem;font-weight:500;cursor:pointer">Copy error</button>
        </div>
        <p style="font-size:.6875rem;color:#475569;margin-top:1.5rem">${DIAG.ts}</p>
      </div>
    </div>`;
}

// ── Root validation ───────────────────────────────────────────
let rootEl = document.getElementById('root');

if (!rootEl) {
  // If the element is missing (e.g. HTML changed), create it
  rootEl = document.createElement('div');
  rootEl.id = 'root';
  document.body.appendChild(rootEl);
  logFatal('startup', '#root element missing — created fallback');
}

// ── Mount React ───────────────────────────────────────────────
let root: Root;
try {
  root = createRoot(rootEl);
} catch (err) {
  logFatal('createRoot', err);
  showInlineFallback(err);
  // Prevent any later code from calling root.render()
  throw err;
}

try {
  root.render(
    <StrictMode>
      <ErrorBoundary diagnostics={DIAG}>
        <App />
      </ErrorBoundary>
    </StrictMode>
  );
} catch (err) {
  logFatal('render', err);
  showInlineFallback(err);
}
