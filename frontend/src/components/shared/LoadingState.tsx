interface LoadingStateProps {
  message?: string;
}

export function LoadingState({ message = 'Loading...' }: LoadingStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <div className="mb-4 flex space-x-2">
        <div className="h-2 w-2 rounded-full bg-blue-500 animate-pulse"></div>
        <div className="h-2 w-2 rounded-full bg-blue-500 animate-pulse" style={{ animationDelay: '0.1s' }}></div>
        <div className="h-2 w-2 rounded-full bg-blue-500 animate-pulse" style={{ animationDelay: '0.2s' }}></div>
      </div>
      <p className="text-gray-400">{message}</p>
    </div>
  );
}
