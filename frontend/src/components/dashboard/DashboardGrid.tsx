/**
 * DashboardGrid — react-grid-layout powered widget grid.
 * Uses plain GridLayout (not Responsive) with our own width measurement
 * to avoid CJS/ESM interop issues with react-grid-layout v2.
 */
import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
// eslint-disable-next-line @typescript-eslint/no-explicit-any
import ReactGridLayout from 'react-grid-layout';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';
import { useDashboardStore, type LayoutItem } from '../../lib/dashboardStore';
import { WIDGET_REGISTRY } from '../../lib/widgetRegistry';
import { WidgetWrapper } from './WidgetWrapper';

// Row height in pixels — each grid unit ≈ 40px
const ROW_HEIGHT = 40;
const COLS = 12;

function useContainerWidth() {
  const ref = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(entries => {
      for (const entry of entries) {
        setWidth(entry.contentRect.width);
      }
    });
    ro.observe(el);
    setWidth(el.clientWidth);
    return () => ro.disconnect();
  }, []);
  return { ref, width };
}

function WidgetFallback() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="animate-pulse text-xs text-neutral-500">Loading...</div>
    </div>
  );
}

export function DashboardGrid() {
  const { layout, visibleWidgets, isLocked, setLayout, removeWidget } = useDashboardStore();
  const { ref: containerRef, width: containerWidth } = useContainerWidth();

  // Filter layout to only include visible widgets
  const activeLayout = useMemo(
    () => layout.filter(item => visibleWidgets.includes(item.i)),
    [layout, visibleWidgets]
  );

  // Responsive: collapse to single column on narrow screens
  const cols = containerWidth < 768 ? 1 : containerWidth < 996 ? 6 : COLS;
  const adjustedLayout = useMemo(() => {
    if (cols === COLS) return activeLayout;
    // Stack widgets vertically for narrow screens
    let yOffset = 0;
    return activeLayout.map(item => {
      const adjusted = { ...item, x: 0, w: cols, y: yOffset };
      yOffset += item.h;
      return adjusted;
    });
  }, [activeLayout, cols]);

  const handleLayoutChange = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (newLayout: any[]) => {
      if (!isLocked && cols === COLS) {
        // Only persist desktop layout changes
        const updatedMap = new Map(newLayout.map((item: LayoutItem) => [item.i, item]));
        const merged = layout.map(item =>
          updatedMap.has(item.i) ? { ...item, ...updatedMap.get(item.i)! } : item
        );
        for (const item of newLayout) {
          if (!layout.find(l => l.i === item.i)) {
            merged.push(item);
          }
        }
        setLayout(merged);
      }
    },
    [isLocked, layout, setLayout, cols]
  );

  return (
    <div ref={containerRef}>
      {containerWidth > 0 && (
        <ReactGridLayout
          className="dashboard-grid"
          layout={adjustedLayout as any}
          cols={cols}
          rowHeight={ROW_HEIGHT}
          width={containerWidth}
          isDraggable={!isLocked}
          isResizable={!isLocked}
          compactType="vertical"
          margin={[16, 16]}
          containerPadding={[16, 16]}
          onLayoutChange={handleLayoutChange as any}
          draggableHandle=".widget-drag-handle"
          useCSSTransforms
        >
          {visibleWidgets.map(widgetId => {
            const meta = WIDGET_REGISTRY[widgetId];
            if (!meta) return null;
            const Component = meta.component;
            return (
              <div key={widgetId}>
                <WidgetWrapper
                  widgetId={widgetId}
                  name={meta.name}
                  isLocked={isLocked}
                  onRemove={() => removeWidget(widgetId)}
                >
                  <Suspense fallback={<WidgetFallback />}>
                    <Component />
                  </Suspense>
                </WidgetWrapper>
              </div>
            );
          })}
        </ReactGridLayout>
      )}
    </div>
  );
}
