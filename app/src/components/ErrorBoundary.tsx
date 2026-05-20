/**
 * ErrorBoundary — wraps any React subtree so that a runtime error in that
 * subtree is caught here and a fallback card is rendered instead of the
 * whole app crashing.  Auth, login, and other siblings are unaffected.
 */

import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  /** Optional custom fallback. Defaults to a generic error card. */
  fallback?: ReactNode;
  /** Label shown in the default fallback card (e.g. "Content Library"). */
  label?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', this.props.label ?? 'section', error, info);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-5 text-sm text-red-200">
          <p className="font-semibold">
            {this.props.label ? `${this.props.label} failed to load` : 'This section failed to load'}
          </p>
          <p className="mt-1 text-xs text-red-300/70">
            {this.state.error?.message ?? 'An unexpected error occurred.'}
          </p>
          <button
            className="mt-3 rounded border border-red-500/40 bg-red-500/10 px-3 py-1 text-xs text-red-200 hover:bg-red-500/20"
            onClick={() => this.setState({ hasError: false, error: null })}
          >
            Retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
