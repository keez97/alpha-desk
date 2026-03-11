import { useState, useEffect, useRef } from 'react';
import { fetchModels, switchModel } from '../../lib/api';

const MODEL_LABELS: Record<string, string> = {
  'claude-sonnet-4': 'Claude Sonnet 4',
  'claude-haiku-3.5': 'Claude Haiku 3.5',
  'gpt-4o': 'GPT-4o',
  'gpt-4o-mini': 'GPT-4o Mini',
  'gemini-2.5-pro': 'Gemini 2.5 Pro',
  'deepseek-chat': 'DeepSeek V3',
  'llama-4-maverick': 'Llama 4 Maverick',
};

export function ModelSelector() {
  const [current, setCurrent] = useState('');
  const [available, setAvailable] = useState<string[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchModels()
      .then((res) => {
        setCurrent(res.current);
        setAvailable(res.available.map((m) => m.key));
      })
      .catch(() => {
        // Silently fail — model selector is non-critical
        setCurrent('claude-sonnet-4');
        setAvailable(['claude-sonnet-4']);
      });
  }, []);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const handleSwitch = async (key: string) => {
    if (key === current) { setOpen(false); return; }
    setLoading(true);
    try {
      const res = await switchModel(key);
      setCurrent(res.current);
    } finally {
      setLoading(false);
      setOpen(false);
    }
  };

  if (!current) return null;

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 rounded px-2 py-1 text-[11px] font-medium text-neutral-500 hover:text-neutral-300 transition-colors"
      >
        <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-500" />
        {loading ? 'Switching…' : MODEL_LABELS[current] || current}
        <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="absolute right-0 top-full z-50 mt-1 w-48 rounded border border-neutral-800 bg-neutral-950 py-1 shadow-xl">
          <div className="px-3 py-1 text-[10px] font-medium uppercase tracking-wider text-neutral-600">
            Model
          </div>
          {available.map((key) => (
            <button
              key={key}
              onClick={() => handleSwitch(key)}
              className={`flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs transition-colors ${
                key === current
                  ? 'bg-neutral-800 text-neutral-200'
                  : 'text-neutral-400 hover:bg-neutral-900 hover:text-neutral-200'
              }`}
            >
              {key === current && (
                <svg className="h-3 w-3 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
              <span className={key !== current ? 'ml-5' : ''}>
                {MODEL_LABELS[key] || key}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
