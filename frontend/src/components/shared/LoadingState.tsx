interface LoadingStateProps {
  message?: string;
}

export function LoadingState({ message = 'Loading...' }: LoadingStateProps) {
  return (
    <div className='flex items-center gap-3 py-6 px-4'>
      <div className='h-4 w-4 animate-spin rounded-full border-2 border-neutral-700 border-t-neutral-400' />
      <p className='text-xs text-neutral-500'>{message}</p>
    </div>
  );
}
