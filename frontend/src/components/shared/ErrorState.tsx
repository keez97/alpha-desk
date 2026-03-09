interface ErrorStateProps {
  error: Error | string;
  onRetry?: () => void;
}

export function ErrorState({ error, onRetry }: ErrorStateProps) {
  const message = error instanceof Error ? error.message : error;

  return (
    <div className="flex flex-col items-center justify-center py-12">
      <div className="mb-4 rounded-lg bg-red-500/10 p-4">
        <p className="text-sm text-red-400">Error</p>
      </div>
      <p className="mb-4 text-center text-gray-400">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
        >
          Try Again
        </button>
      )}
    </div>
  );
}
