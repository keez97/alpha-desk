import { useRef, useEffect, useState, useCallback } from 'react';
import type { RRGData } from '../../lib/api';

interface RRGChartProps {
  data: RRGData;
}

// Sector colors — distinct, colorblind-friendly palette
const SECTOR_COLORS: Record<string, string> = {
  XLK: '#3b82f6',   // blue
  XLV: '#10b981',   // emerald
  XLF: '#f59e0b',   // amber
  XLY: '#ef4444',   // red
  XLP: '#8b5cf6',   // violet
  XLE: '#f97316',   // orange
  XLRE: '#06b6d4',  // cyan
  XLI: '#ec4899',   // pink
  XLU: '#84cc16',   // lime
  XLC: '#6366f1',   // indigo
  XLCQ: '#6366f1',  // indigo (same as XLC)
};

// Quadrant background colors
const QUADRANTS = {
  leading:    { color: 'rgba(34, 197, 94, 0.06)',  label: 'Leading',    labelColor: '#22c55e' },
  improving:  { color: 'rgba(59, 130, 246, 0.06)', label: 'Improving',  labelColor: '#3b82f6' },
  lagging:    { color: 'rgba(239, 68, 68, 0.06)',  label: 'Lagging',    labelColor: '#ef4444' },
  weakening:  { color: 'rgba(234, 179, 8, 0.06)',  label: 'Weakening',  labelColor: '#eab308' },
};

function catmullRomSpline(points: [number, number][], tension: number = 0.5): [number, number][] {
  if (points.length < 2) return points;
  const result: [number, number][] = [];
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[Math.max(0, i - 1)];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[Math.min(points.length - 1, i + 2)];
    const steps = 12;
    for (let t = 0; t <= steps; t++) {
      const s = t / steps;
      const s2 = s * s;
      const s3 = s2 * s;
      const x = 0.5 * (
        (2 * p1[0]) +
        (-p0[0] + p2[0]) * s +
        (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * s2 +
        (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * s3
      );
      const y = 0.5 * (
        (2 * p1[1]) +
        (-p0[1] + p2[1]) * s +
        (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * s2 +
        (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * s3
      );
      result.push([x, y]);
    }
  }
  return result;
}

export function RRGChart({ data }: RRGChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [animFrame, setAnimFrame] = useState(-1); // -1 = show all, 0..N = animation frame
  const [isPlaying, setIsPlaying] = useState(false);
  const [hoveredSector, setHoveredSector] = useState<string | null>(null);
  const animRef = useRef<number | null>(null);
  const frameRef = useRef(-1);

  // Determine max trail length
  const maxTrailLen = Math.max(...data.sectors.map(s => s.history.length), 1);

  // Compute axis ranges
  const allRatios = data.sectors.flatMap(s => s.history.map(h => h.rsRatio));
  const allMomentums = data.sectors.flatMap(s => s.history.map(h => h.rsMomentum));
  const padding = 0.15;
  const xMin = Math.min(95, ...allRatios) * (1 - padding);
  const xMax = Math.max(105, ...allRatios) * (1 + padding);
  const yMin = Math.min(-5, ...allMomentums) * (allMomentums.some(m => m < 0) ? (1 + padding) : (1 - padding));
  const yMax = Math.max(5, ...allMomentums) * (1 + padding);

  // Margins
  const margin = { top: 40, right: 30, bottom: 50, left: 60 };

  const toCanvasX = useCallback((val: number) => {
    const plotW = dimensions.width - margin.left - margin.right;
    return margin.left + ((val - xMin) / (xMax - xMin)) * plotW;
  }, [dimensions.width, xMin, xMax]);

  const toCanvasY = useCallback((val: number) => {
    const plotH = dimensions.height - margin.top - margin.bottom;
    return margin.top + ((yMax - val) / (yMax - yMin)) * plotH;
  }, [dimensions.height, yMin, yMax]);

  // Resize observer
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const ro = new ResizeObserver(entries => {
      const { width } = entries[0].contentRect;
      setDimensions({ width, height: Math.max(500, width * 0.7) });
    });
    ro.observe(container);
    return () => ro.disconnect();
  }, []);

  // Draw
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = dimensions.width * dpr;
    canvas.height = dimensions.height * dpr;
    ctx.scale(dpr, dpr);

    const { width, height } = dimensions;
    const plotX = margin.left;
    const plotY = margin.top;
    const plotW = width - margin.left - margin.right;
    const plotH = height - margin.top - margin.bottom;

    // Clear
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, width, height);

    // Draw quadrant backgrounds
    const cx100 = toCanvasX(100);
    const cy0 = toCanvasY(0);

    // Leading (top-right): green
    ctx.fillStyle = QUADRANTS.leading.color;
    ctx.fillRect(cx100, plotY, plotX + plotW - cx100, cy0 - plotY);

    // Improving (top-left): blue
    ctx.fillStyle = QUADRANTS.improving.color;
    ctx.fillRect(plotX, plotY, cx100 - plotX, cy0 - plotY);

    // Lagging (bottom-left): red
    ctx.fillStyle = QUADRANTS.lagging.color;
    ctx.fillRect(plotX, cy0, cx100 - plotX, plotY + plotH - cy0);

    // Weakening (bottom-right): yellow
    ctx.fillStyle = QUADRANTS.weakening.color;
    ctx.fillRect(cx100, cy0, plotX + plotW - cx100, plotY + plotH - cy0);

    // Quadrant labels
    ctx.font = '11px Inter, system-ui, sans-serif';
    ctx.globalAlpha = 0.5;
    ctx.fillStyle = QUADRANTS.leading.labelColor;
    ctx.fillText('LEADING', plotX + plotW - 70, plotY + 20);
    ctx.fillStyle = QUADRANTS.improving.labelColor;
    ctx.fillText('IMPROVING', plotX + 10, plotY + 20);
    ctx.fillStyle = QUADRANTS.lagging.labelColor;
    ctx.fillText('LAGGING', plotX + 10, plotY + plotH - 10);
    ctx.fillStyle = QUADRANTS.weakening.labelColor;
    ctx.fillText('WEAKENING', plotX + plotW - 80, plotY + plotH - 10);
    ctx.globalAlpha = 1;

    // Grid lines
    ctx.strokeStyle = 'rgba(255,255,255,0.04)';
    ctx.lineWidth = 1;
    const xTicks = 8;
    const yTicks = 6;
    for (let i = 0; i <= xTicks; i++) {
      const val = xMin + (i / xTicks) * (xMax - xMin);
      const x = toCanvasX(val);
      ctx.beginPath();
      ctx.moveTo(x, plotY);
      ctx.lineTo(x, plotY + plotH);
      ctx.stroke();
    }
    for (let i = 0; i <= yTicks; i++) {
      const val = yMin + (i / yTicks) * (yMax - yMin);
      const y = toCanvasY(val);
      ctx.beginPath();
      ctx.moveTo(plotX, y);
      ctx.lineTo(plotX + plotW, y);
      ctx.stroke();
    }

    // Reference lines at 100 (x) and 0 (y)
    ctx.strokeStyle = 'rgba(255,255,255,0.15)';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    // Vertical at RS-Ratio = 100
    ctx.beginPath();
    ctx.moveTo(cx100, plotY);
    ctx.lineTo(cx100, plotY + plotH);
    ctx.stroke();
    // Horizontal at RS-Momentum = 0
    ctx.beginPath();
    ctx.moveTo(plotX, cy0);
    ctx.lineTo(plotX + plotW, cy0);
    ctx.stroke();
    ctx.setLineDash([]);

    // Axis labels
    ctx.fillStyle = '#525252';
    ctx.font = '10px Inter, system-ui, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('RS-Ratio', plotX + plotW / 2, height - 8);
    ctx.save();
    ctx.translate(16, plotY + plotH / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText('RS-Momentum', 0, 0);
    ctx.restore();

    // Axis tick labels
    ctx.font = '10px Inter, system-ui, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillStyle = '#404040';
    for (let i = 0; i <= xTicks; i++) {
      const val = xMin + (i / xTicks) * (xMax - xMin);
      ctx.fillText(val.toFixed(1), toCanvasX(val), plotY + plotH + 18);
    }
    ctx.textAlign = 'right';
    for (let i = 0; i <= yTicks; i++) {
      const val = yMin + (i / yTicks) * (yMax - yMin);
      ctx.fillText(val.toFixed(1), plotX - 8, toCanvasY(val) + 4);
    }

    // Draw sectors
    const frameLimit = animFrame === -1 ? maxTrailLen : Math.min(animFrame + 1, maxTrailLen);

    for (const sector of data.sectors) {
      const color = SECTOR_COLORS[sector.ticker] || '#9ca3af';
      const history = sector.history.slice(0, frameLimit);
      if (history.length === 0) continue;

      const isHovered = hoveredSector === sector.ticker;
      const alphaMultiplier = hoveredSector && !isHovered ? 0.25 : 1;

      // Smooth trail
      if (history.length >= 2) {
        const rawPoints: [number, number][] = history.map(h => [
          toCanvasX(h.rsRatio),
          toCanvasY(h.rsMomentum)
        ]);
        const smoothPoints = catmullRomSpline(rawPoints);

        // Draw trail with fade
        for (let i = 1; i < smoothPoints.length; i++) {
          const progress = i / smoothPoints.length;
          const alpha = (0.15 + 0.85 * progress) * alphaMultiplier;
          ctx.strokeStyle = color;
          ctx.globalAlpha = alpha;
          ctx.lineWidth = isHovered ? 3 : 2;
          ctx.beginPath();
          ctx.moveTo(smoothPoints[i - 1][0], smoothPoints[i - 1][1]);
          ctx.lineTo(smoothPoints[i][0], smoothPoints[i][1]);
          ctx.stroke();
        }
        ctx.globalAlpha = 1;
      }

      // Current position bubble
      const current = history[history.length - 1];
      const cx = toCanvasX(current.rsRatio);
      const cy = toCanvasY(current.rsMomentum);

      // Bubble size based on absolute momentum (bigger = stronger move)
      const momentumMag = Math.abs(current.rsMomentum);
      const baseRadius = isHovered ? 10 : 7;
      const radius = baseRadius + Math.min(momentumMag * 0.8, 8);

      // Bubble
      ctx.globalAlpha = alphaMultiplier;
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.strokeStyle = 'rgba(255,255,255,0.3)';
      ctx.lineWidth = 1.5;
      ctx.stroke();
      ctx.globalAlpha = 1;

      // Ticker label
      ctx.globalAlpha = alphaMultiplier;
      ctx.fillStyle = '#d4d4d4';
      ctx.font = `${isHovered ? 'bold ' : ''}11px Inter, system-ui, sans-serif`;
      ctx.textAlign = 'center';
      ctx.fillText(sector.ticker, cx, cy - radius - 5);
      ctx.globalAlpha = 1;
    }

    // Plot border
    ctx.strokeStyle = 'rgba(255,255,255,0.15)';
    ctx.lineWidth = 1;
    ctx.strokeRect(plotX, plotY, plotW, plotH);

  }, [data, dimensions, animFrame, hoveredSector, toCanvasX, toCanvasY, xMin, xMax, yMin, yMax, maxTrailLen]);

  // Mouse interaction for hover
  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    const frameLimit = animFrame === -1 ? maxTrailLen : Math.min(animFrame + 1, maxTrailLen);
    let closest: string | null = null;
    let closestDist = 30; // Max hover distance in pixels

    for (const sector of data.sectors) {
      const history = sector.history.slice(0, frameLimit);
      if (history.length === 0) continue;
      const current = history[history.length - 1];
      const cx = toCanvasX(current.rsRatio);
      const cy = toCanvasY(current.rsMomentum);
      const dist = Math.sqrt((mx - cx) ** 2 + (my - cy) ** 2);
      if (dist < closestDist) {
        closestDist = dist;
        closest = sector.ticker;
      }
    }
    setHoveredSector(closest);
  }, [data, animFrame, maxTrailLen, toCanvasX, toCanvasY]);

  // Animation playback
  useEffect(() => {
    if (!isPlaying) return;

    frameRef.current = animFrame === -1 ? 0 : animFrame;
    const tick = () => {
      frameRef.current += 1;
      if (frameRef.current >= maxTrailLen) {
        setIsPlaying(false);
        setAnimFrame(-1);
        return;
      }
      setAnimFrame(frameRef.current);
      animRef.current = requestAnimationFrame(() => {
        setTimeout(tick, 150); // 150ms per frame for visible stepping
      });
    };
    tick();

    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, [isPlaying, maxTrailLen]);

  const togglePlay = () => {
    if (isPlaying) {
      setIsPlaying(false);
    } else {
      setAnimFrame(0);
      setIsPlaying(true);
    }
  };

  return (
    <div ref={containerRef} className="w-full">
      {/* Legend */}
      <div className="flex flex-wrap gap-2 mb-2">
        {data.sectors.map(sector => (
          <div
            key={sector.ticker}
            className="flex items-center gap-1 cursor-pointer transition-opacity"
            style={{ opacity: hoveredSector && hoveredSector !== sector.ticker ? 0.3 : 1 }}
            onMouseEnter={() => setHoveredSector(sector.ticker)}
            onMouseLeave={() => setHoveredSector(null)}
          >
            <div
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: SECTOR_COLORS[sector.ticker] || '#525252' }}
            />
            <span className="text-[10px] text-neutral-500">
              {sector.ticker}
            </span>
          </div>
        ))}
      </div>

      {/* Canvas */}
      <canvas
        ref={canvasRef}
        style={{ width: dimensions.width, height: dimensions.height }}
        className="rounded"
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHoveredSector(null)}
      />

      {/* Animation Controls */}
      <div className="flex items-center gap-3 mt-2">
        <button
          onClick={togglePlay}
          className="flex items-center gap-1.5 px-2 py-1 rounded text-[11px] text-neutral-400 hover:text-neutral-200 border border-neutral-800 hover:border-neutral-700 transition-colors"
        >
          {isPlaying ? 'Pause' : 'Play'}
        </button>

        <input
          type="range"
          min={0}
          max={maxTrailLen - 1}
          value={animFrame === -1 ? maxTrailLen - 1 : animFrame}
          onChange={(e) => {
            setIsPlaying(false);
            setAnimFrame(parseInt(e.target.value));
          }}
          className="flex-1"
        />

        <button
          onClick={() => { setIsPlaying(false); setAnimFrame(-1); }}
          className="px-2 py-1 rounded text-[11px] text-neutral-500 hover:text-neutral-300 transition-colors"
        >
          All
        </button>

        <span className="text-[10px] text-neutral-600 min-w-[50px] text-right">
          {animFrame === -1 ? 'All' : `${animFrame + 1}/${maxTrailLen}`}
        </span>
      </div>
    </div>
  );
}
