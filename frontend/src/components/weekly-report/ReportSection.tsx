import { useState } from 'react';

interface ReportSectionProps {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}

export function ReportSection({ title, children, defaultOpen = true }: ReportSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-800/30">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between px-6 py-4 hover:bg-gray-700/20 transition-colors"
      >
        <h3 className="font-semibold text-white">{title}</h3>
        <span className="text-gray-400 text-xl">{isOpen ? '−' : '+'}</span>
      </button>

      {isOpen && (
        <div className="border-t border-gray-700 px-6 py-4">
          {children}
        </div>
      )}
    </div>
  );
}
