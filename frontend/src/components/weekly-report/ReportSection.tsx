import { useState } from 'react';

interface ReportSectionProps {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}

export function ReportSection({ title, children, defaultOpen = true }: ReportSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="border border-neutral-800 rounded">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between px-4 py-2 hover:bg-neutral-900/50 transition-colors"
      >
        <span className="text-xs font-medium text-neutral-300">{title}</span>
        <span className="text-neutral-600 text-xs">{isOpen ? '−' : '+'}</span>
      </button>

      {isOpen && (
        <div className="border-t border-neutral-800 px-4 py-3">
          {children}
        </div>
      )}
    </div>
  );
}
