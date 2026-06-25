import type { EChartsOption } from "echarts";
import type {
  AnalyticsSummaryResponse,
  TimelineResponse,
} from "../../api/generated/types.gen";

export function timelineOption(data: TimelineResponse): EChartsOption {
  return {
    animationDuration: 500,
    color: ["#087e8b", "#f2a900"],
    tooltip: { trigger: "axis" },
    legend: {
      data: ["Eventos", "Sesiones"],
      top: 0,
      right: 0,
      textStyle: { color: "#495057" },
    },
    grid: { top: 38, right: 18, bottom: 28, left: 42 },
    xAxis: {
      type: "category",
      boundaryGap: false,
      data: data.points.map((point) =>
        new Intl.DateTimeFormat("es-AR", {
          hour: "2-digit",
          minute: "2-digit",
        }).format(new Date(point.timestamp)),
      ),
      axisLine: { lineStyle: { color: "#ced4da" } },
      axisLabel: { color: "#6c757d" },
    },
    yAxis: {
      type: "value",
      minInterval: 1,
      axisLabel: { color: "#6c757d" },
      splitLine: { lineStyle: { color: "#e9ecef" } },
    },
    series: [
      {
        name: "Eventos",
        type: "line",
        smooth: 0.2,
        showSymbol: false,
        areaStyle: { opacity: 0.08 },
        data: data.points.map((point) => point.events),
      },
      {
        name: "Sesiones",
        type: "line",
        smooth: 0.2,
        showSymbol: false,
        data: data.points.map((point) => point.sessions),
      },
    ],
  };
}

export function riskOption(summary: AnalyticsSummaryResponse): EChartsOption {
  return {
    animationDuration: 500,
    color: ["#3a9d5d", "#f2a900", "#f06c3b", "#c1121f"],
    tooltip: { trigger: "item" },
    legend: {
      bottom: 0,
      left: "center",
      textStyle: { color: "#495057" },
    },
    series: [
      {
        name: "Riesgo",
        type: "pie",
        radius: ["48%", "72%"],
        center: ["50%", "43%"],
        label: { show: false },
        data: [
          { name: "Bajo", value: summary.risk_low },
          { name: "Medio", value: summary.risk_medium },
          { name: "Alto", value: summary.risk_high },
          { name: "Crítico", value: summary.risk_critical },
        ],
      },
    ],
  };
}
