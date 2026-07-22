import { Component, type ReactNode, type ErrorInfo } from 'react';

interface Props {
  tabName: string;
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class TabErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error(`[SmartPip TabErrorBoundary] ${this.props.tabName} crashed:`, error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-4 sm:p-6 rounded-xl bg-slate-900 border border-slate-800 text-center space-y-3">
          <div className="w-10 h-10 mx-auto rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 text-lg">
            ⚠
          </div>
          <h2 className="text-sm font-semibold text-slate-200">
            {this.props.tabName} failed to load
          </h2>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            This tab encountered an error but the rest of the app is unaffected. You can try reloading.
          </p>
          {this.state.error && (
            <p className="text-[0.65rem] font-mono text-slate-500 bg-slate-950 rounded-lg p-2.5 border border-slate-800 text-left overflow-auto max-h-24">
              {this.state.error.message}
            </p>
          )}
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="px-3 py-1.5 rounded-lg bg-blue-500/15 text-blue-400 text-xs font-medium hover:bg-blue-500/25 transition-colors"
          >
            Try again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
