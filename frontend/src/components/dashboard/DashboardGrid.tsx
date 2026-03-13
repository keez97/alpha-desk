/**
 * DashboardGrid — react-grid-layout v2 powered widget grid.
 * Wraps all visible widgets in a draggable/resizable grid.
 */
import { Suspense, useCallback, useMemo, useRef } from 'react';
/* eslint-disable @typescript-eslint/no-explicit-any */
// react-grid-layout v2 uses named exports; types from @types/react-grid-layout are for v1
import * as RGL from 'react-grid-layout';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';
import { useDashboardStore, type LayoutItem } from '../../lib/dashboardStore';
import { WIDGET_REGISTRY } from '../../lib/widgetRegistry';
import { WidgetWrapper } from './WidgetWrapper';

// v2 API: named exports — use namespace import for correct CJS/ESM interop
const ResponsiveGridLayout = (RGL as any).ResponsiveGridLayout;
const useContainerWidth = (RGL as any).useContainerWidth;

// Row height in pixels — each grid unit ≈ 40px
const ROW_HEIGHT = 40;
const COLS = { lg: 12, md: 12, sm: 6, xs: 4, xxs: 2 };
const BREAKPOINTS = { lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 };

function WidgetFallback() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="animate-pulse text-xs text-neutral-500">Loading...</div>
    </div>
  );
}

export function DashboardGrid() {
  const { layout, visibleWidgets, isLocked, setLayout, removeWidget } = useDashboardStore();
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth] = useContainerWidth(containerRef);

  // Filter layout to only include visible widgets
  const activeLayout = useMemo(
    () => layout.filter((item: LayoutItem) => visibleWidgets.includes(item.i)),
    [layout, visibleWidgets]
  );

  // Generate responsive layouts — sm/xs/xxs get single-column stacking
  const responsiveLayouts = useMemo(() => {
    const sm = activeLayout.map((item: LayoutItem, idx: number) => ({
      ...item,
      x: 0,
      w: 6,
      y: idx * item.h,
    }));
    const xs = activeLayout.map((item: LayoutItem, idx: number) => ({
      ...item,
      x: 0,
      w: 4,
      y: idx * item.h,
    }));
    const xxs = activeLayout.map((item: LayoutItem, idx: number) => ({
      ...item,
      x: 0,
      w: 2,
      y: idx * item.h,
    }));
    return { lg: activeLayout, md: activeLayout, sm, xs, xxs };
  }, [activeLayout]);

  const handleLayoutChange = useCallback(
    (currentLayout: LayoutItem[]) => {
      if (!isLocked) {
        const updatedMap = new Map(currentLayout.map((item: LayoutItem) => [item.i, item]));
        const merged = layout.map((item: LayoutItem) =>
          updatedMap.has(item.i) ? { ...item, ...updatedMap.get(item.i)! } : item
        );
        for (const item of currentLayout) {
          if (!layout.find((l: LayoutItem) => l.i === item.i)) {
            merged.push(item);
          }
        }
        setLayout(merged);
      }
    },
    [isLocked, layout, setLayout]
  );

  return (
    <div ref={containerRef}>
      {containerWidth > 0 && (
        <ResponsiveGridLayout
          className="dashboard-grid"
          width={containerWidth}
          layouts={responsiveLayouts}
          breakpoints={BREAKPOINTS}
          cols={COLS}
          rowHeight={ROW_HEIGHT}
          isDraggable={!isLocked}
          isResizable={!isLocked}
          compactType="vertical"
          margin={[16, 16]}
          containerPadding={[16, 16]}
          onLayoutChange={handleLayoutChange}
          draggableHandle=".widget-drag-handle"
          useCSSTransforms
        >
          {visibleWidgets.map((widgetId: string) => {
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
        </ResponsiveGridLayout>
      )}
    </div>
  );
}
