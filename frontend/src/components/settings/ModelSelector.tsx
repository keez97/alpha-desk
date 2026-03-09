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
    fetchModels().then((res) => {
      setCurrent(res.current);
      setAvailable(res.available.map((m) => m.key));
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
        className="flex items-center gap-1.5 rounded-md border border-gray-600 bg-gray-800 px-3 py-1.5 text-xs font-medium text-gray-300 hover:border-blue-500 hover:text-white transition-colors"
      >
        <span className="inline-block h-2 w-2 rounded-full bg-green-400" />
        {loading ? 'Switching…' : MODEL_LABELS[current] || current}
        <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="absolute right-0 top-full z-50 mt-1 w-52 rounded-lg border border-gray-600 bg-gray-800 py-1 shadow-xl">
          <div className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-gray-500">
            LLM Model
          </div>
          {available.map((key) => (
            <button
              key={key}
              onClick={() => handleSwitch(key)}
              className={`flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors ${
                key === current
                  ? 'bg-blue-600/20 text-blue-400'
                  : 'text-gray-300 hover:bg-gray-700'
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
