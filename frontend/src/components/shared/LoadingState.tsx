interface LoadingStateProps {
  message?: string;
}

export function LoadingState({ message = 'Loading...' }: LoadingStateProps) {
  return (
    <div className='flex flex-col items-center justify-center py-12'>
      <div className='flex space-x-1.5 mb-4'>
        <div className='w-2.5 h-2.5 bg-blue-500 rounded-full animate-bounce' style={{ animationDelay: '0ms' }}></div>
        <div className='w-2.5 h-2.5 bg-blue-500 rounded-full animate-bounce' style={{ animationDelay: '150ms' }}></div>
        <div className='w-2.5 h-2.5 bg-blue-500 rounded-full animate-bounce' style={{ animationDelay: '300ms' }}></div>
      </div>
      <p className='text-sm text-gray-400'>{message}</p>
    </div>
  );
}
