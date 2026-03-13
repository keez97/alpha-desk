/* eslint-disable @typescript-eslint/no-explicit-any */
declare module 'react-grid-layout' {
  import { Component } from 'react';

  interface LayoutItem {
    i: string;
    x: number;
    y: number;
    w: number;
    h: number;
    minW?: number;
    minH?: number;
    maxW?: number;
    maxH?: number;
    static?: boolean;
    isDraggable?: boolean;
    isResizable?: boolean;
  }

  interface GridLayoutProps {
    className?: string;
    layout?: LayoutItem[];
    cols?: number;
    rowHeight?: number;
    width: number;
    isDraggable?: boolean;
    isResizable?: boolean;
    compactType?: 'vertical' | 'horizontal' | null;
    margin?: [number, number];
    containerPadding?: [number, number];
    onLayoutChange?: (layout: LayoutItem[]) => void;
    draggableHandle?: string;
    useCSSTransforms?: boolean;
    children?: React.ReactNode;
    [key: string]: any;
  }

  export default class ReactGridLayout extends Component<GridLayoutProps> {}

  export class ResponsiveGridLayout extends Component<any> {}
  export function useContainerWidth(ref: React.RefObject<HTMLElement>): [number];
  export function getBreakpointFromWidth(breakpoints: Record<string, number>, width: number): string;
}
