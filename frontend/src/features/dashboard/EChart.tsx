import { useEffect, useRef } from "react";
import type { EChartsOption } from "echarts";
import * as echarts from "echarts/core";
import { LineChart, PieChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([
  LineChart,
  PieChart,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  CanvasRenderer,
]);

type Props = {
  option: EChartsOption;
  label: string;
};

export function EChart({ option, label }: Props) {
  const elementRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!elementRef.current) return;
    const chart = echarts.init(elementRef.current);
    chart.setOption(option);
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(elementRef.current);
    return () => {
      observer.disconnect();
      chart.dispose();
    };
  }, [option]);

  return (
    <div
      ref={elementRef}
      className="chart-canvas"
      role="img"
      aria-label={label}
    />
  );
}
