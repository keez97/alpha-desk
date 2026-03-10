interface ErrorStateProps {
  error: Error | string;
  onRetry?: () => void;
}

export function ErrorState({ error, onRetry }: ErrorStateProps) {
  let message = error instanceof Error ? error.message : error;

  // Convert network errors to user-friendly message
  if (message.includes('Network Error') || message.includes('ERR_NETWORK')) {
    message = 'Unable to connect to server';
  }

  return (
    <div className="flex items-center gap-3 py-4 px-4">
      <span className="text-xs text-red-400/80">Error:</span>
      <span className="text-xs text-neutral-400 flex-1">{message}</span>
      {onRetry && (
        <button
          onClick={onRetry}
          className="rounded px-3 py-1 text-xs font-medium text-neutral-400 border border-neutral-800 hover:text-neutral-200 hover:border-neutral-700 transition-colors whitespace-nowrap"
        >
          Retry
        </button>
      )}
    </div>
  );
}
