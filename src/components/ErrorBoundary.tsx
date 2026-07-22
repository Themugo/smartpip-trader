import { Component, type ReactNode, type ErrorInfo } from 'react';

// ── Types ──────────────────────────────────────────────────────

interface Diagnostics {
  env: {
    timestamp: string;
    variables: { name: string; required: boolean; present: boolean; preview: string }[];
    allRequiredPresent: boolean;
  };
  envOk: boolean;
  ua: string;
  ts: string;
}

interface Props {
  children: ReactNode;
  diagnostics?: Diagnostics;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  errorId: string;
  copied: boolean;
}

// ── Error classification ──────────────────────────────────────

type ErrorCategory = 'component' | 'api' | 'auth' | 'environment' | 'unknown';

function classifyError(error: Error): ErrorCategory {
  const msg = (error.message || '').toLowerCase();
  const name = (error.name || '').toLowerCase();

  // Environment / config
  if (
    msg.includes('supabase') ||
    msg.includes('vite_') ||
    msg.includes('env') ||
    msg.includes('undefined') && msg.includes('url') ||
    msg.includes('missing') && msg.includes('environment')
  ) {
    return 'environment';
  }

  // Authentication
  if (
    msg.includes('auth') ||
    msg.includes('session') ||
    msg.includes('token') ||
    msg.includes('unauthorized') ||
    msg.includes('401')
  ) {
    return 'auth';
  }

  // Network / API
  if (
    msg.includes('fetch') ||
    msg.includes('network') ||
    msg.includes('econnrefused') ||
    msg.includes('timeout') ||
    msg.includes('http') ||
    name === 'typeerror' && msg.includes('failed to fetch')
  ) {
    return 'api';
  }

  return 'component';
}

const CATEGORY_META: Record<ErrorCategory, { label: string; icon: string; color: string; hint: string }> = {
  environment: {
    label: 'Environment Error',
    icon: '⚙',
    color: 'amber',
    hint: 'A required environment variable is missing or invalid. Check your VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY settings.',
  },
  auth: {
    label: 'Authentication Error',
    icon: '🔒',
    color: 'violet',
    hint: 'The sign-in process failed. Your session may have expired or the auth service is unreachable.',
  },
  api: {
    label: 'Network Error',
    icon: '📡',
    color: 'sky',
    hint: 'A network request failed. The API server may be down or your connection was interrupted.',
  },
  component: {
    label: 'Component Crash',
    icon: '💥',
    color: 'red',
    hint: 'A UI component threw an unexpected error during rendering.',
  },
  unknown: {
    label: 'Unexpected Error',
    icon: '⚠',
    color: 'red',
    hint: 'Something unexpected happened. The error details below can help with debugging.',
  },
};

// ── Color mapping (Tailwind classes) ──────────────────────────

const COLOR: Record<string, { bg: string; border: string; text: string; badge: string }> = {
  red:    { bg: 'bg-red-500/10',    border: 'border-red-500/20',    text: 'text-red-400',    badge: 'bg-red-500/20 text-red-400' },
  amber:  { bg: 'bg-amber-500/10',  border: 'border-amber-500/20',  text: 'text-amber-400',  badge: 'bg-amber-500/20 text-amber-400' },
  sky:    { bg: 'bg-sky-500/10',    border: 'border-sky-500/20',    text: 'text-sky-400',    badge: 'bg-sky-500/20 text-sky-400' },
  violet: { bg: 'bg-violet-500/10', border: 'border-violet-500/20', text: 'text-violet-400', badge: 'bg-violet-500/20 text-violet-400' },
};

// ── Component ──────────────────────────────────────────────────

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: '',
      copied: false,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return {
      hasError: true,
      error,
      errorId: `ERR-${Date.now().toString(36).toUpperCase()}`,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo });

    // Structured console log for production debugging
    const category = classifyError(error);
    console.groupCollapsed(
      `%c[SmartPip ErrorBoundary] ${CATEGORY_META[category].label}`,
      `color: ${COLOR[CATEGORY_META[category].color]?.text ?? '#f87171'}; font-weight: bold`
    );
    console.error('Error:', error);
    console.error('Component stack:', errorInfo.componentStack);
    console.table({
      'Error ID': this.state.errorId,
      Category: category,
      Message: error.message,
      'App version': this.props.diagnostics?.ts ?? 'unknown',
      'User agent': this.props.diagnostics?.ua ?? 'unknown',
    });
    console.groupEnd();
  }

  handleCopy = async () => {
    const { error, errorInfo, errorId } = this.state;
    const text = [
      `SmartPip Error Report`,
      `ID: ${errorId}`,
      `Time: ${new Date().toISOString()}`,
      `Message: ${error?.message}`,
      `Stack: ${error?.stack}`,
      `Component stack: ${errorInfo?.componentStack}`,
      `User agent: ${navigator.userAgent}`,
      `Env: ${JSON.stringify(this.props.diagnostics?.env ?? {})}`,
    ].join('\n');

    try {
      await navigator.clipboard.writeText(text);
      this.setState({ copied: true });
      setTimeout(() => this.setState({ copied: false }), 2000);
    } catch {
      // Clipboard API may be denied
    }
  };

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    const { error, errorInfo, errorId, copied } = this.state;
    const category = classifyError(error!);
    const meta = CATEGORY_META[category];
    const colors = COLOR[meta.color] ?? COLOR.red;

    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4 sm:p-6">
        <div className="max-w-lg w-full space-y-5">
          {/* Icon + Title */}
          <div className="text-center space-y-3">
            <div className={`w-14 h-14 mx-auto rounded-2xl ${colors.bg} border ${colors.border} flex items-center justify-center text-2xl`}>
              {meta.icon}
            </div>
            <div>
              <span className={`inline-block text-[0.65rem] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full ${colors.badge} mb-2`}>
                {meta.label}
              </span>
              <h1 className="text-lg font-semibold text-slate-100">
                Something went wrong
              </h1>
            </div>
            <p className="text-sm text-slate-400 leading-relaxed max-w-sm mx-auto">
              {meta.hint}
            </p>
          </div>

          {/* Error details */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-slate-800">
              <span className="text-xs font-medium text-slate-500">Error details</span>
              <span className="text-[0.65rem] font-mono text-slate-600">{errorId}</span>
            </div>
            <div className="px-4 py-3 space-y-2">
              <p className="text-xs font-mono text-red-400 break-all leading-relaxed">
                {error?.message}
              </p>
              {error?.stack && (
                <details className="group">
                  <summary className="text-[0.65rem] text-slate-500 cursor-pointer hover:text-slate-400 select-none">
                    Stack trace
                  </summary>
                  <pre className="mt-2 text-[0.65rem] font-mono text-slate-500 whitespace-pre-wrap break-all max-h-40 overflow-auto leading-relaxed">
                    {error.stack}
                  </pre>
                </details>
              )}
              {errorInfo?.componentStack && (
                <details className="group">
                  <summary className="text-[0.65rem] text-slate-500 cursor-pointer hover:text-slate-400 select-none">
                    Component stack
                  </summary>
                  <pre className="mt-2 text-[0.65rem] font-mono text-slate-500 whitespace-pre-wrap break-all max-h-40 overflow-auto leading-relaxed">
                    {errorInfo.componentStack}
                  </pre>
                </details>
              )}
            </div>
          </div>

          {/* Env diagnostics */}
          {this.props.diagnostics && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl px-4 py-3">
              <p className="text-[0.65rem] font-medium text-slate-500 mb-2">Environment</p>
              <div className="flex flex-wrap gap-2">
                {this.props.diagnostics.env.variables.map((v) => (
                  <span
                    key={v.name}
                    className={`text-[0.6rem] font-mono px-2 py-0.5 rounded-full border ${
                      v.present
                        ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                        : 'bg-amber-500/10 border-amber-500/20 text-amber-400'
                    }`}
                  >
                    {v.present ? '✓' : '✗'} {v.name}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => window.location.reload()}
              className="flex-1 px-4 py-2.5 rounded-xl bg-blue-500/15 border border-blue-500/25 text-blue-400 text-sm font-medium hover:bg-blue-500/25 transition-colors"
            >
              Reload page
            </button>
            <button
              onClick={this.handleCopy}
              className="flex-1 px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-slate-300 text-sm font-medium hover:bg-slate-750 transition-colors"
            >
              {copied ? 'Copied!' : 'Copy error report'}
            </button>
          </div>
        </div>
      </div>
    );
  }
}
