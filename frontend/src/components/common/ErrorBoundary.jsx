/**
 * @file Global error boundary: catches render errors and shows a recovery
 * panel instead of a blank screen.
 */
import { Component } from "react";

/**
 * Class-based boundary wrapping the application shell.
 */
export default class ErrorBoundary extends Component {
  /**
   * Initialise boundary state.
   * @param {object} props - Component props.
   */
  constructor(props) {
    super(props);
    this.state = { hasError: false, message: "" };
  }

  /**
   * React lifecycle: derive state from a render-phase error.
   * @param {Error} error - The thrown error.
   * @returns {{hasError: boolean, message: string}} Updated state.
   */
  static getDerivedStateFromError(error) {
    return { hasError: true, message: String(error?.message || error) };
  }

  /**
   * React lifecycle: log the error for diagnostics.
   * @param {Error} error - The thrown error.
   * @param {object} info - React component stack.
   */
  componentDidCatch(error, info) {
    console.error("UI ErrorBoundary:", error, info?.componentStack);
  }

  /**
   * Render children, or a recovery panel after an error.
   * @returns {JSX.Element} Error screen or wrapped children.
   */
  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-dark-bg p-6">
          <div className="max-w-md rounded-lg border border-rose-500/30 bg-slate-900 p-6 text-center">
            <h1 className="text-lg font-semibold text-rose-300">Something went wrong</h1>
            <p className="mt-2 text-sm text-slate-400">{this.state.message}</p>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="mt-4 rounded border border-quantum-blue/40 bg-quantum-blue/10 px-4 py-2 text-sm text-cyan-200 hover:bg-quantum-blue/20"
            >
              Reload dashboard
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
