import {
  createChart,
  ColorType,
  CrosshairMode,
  type IChartApi,
  type ISeriesApi,
  type IPriceLine,
  type UTCTimestamp,
} from "lightweight-charts";
import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
} from "react";
import type { Candle } from "../types";

// Reveal one hidden candle every REVEAL_INTERVAL_MS for the "market ticking
// forward" animation.
const REVEAL_INTERVAL_MS = 180;
// Anchor the sequential day index onto a fake timeline. The value is arbitrary;
// what matters is that candles are unique and ascending. Real dates are never
// shown — the axis is relabelled to "D{n}".
const SECONDS_PER_DAY = 86400;

const UP = "#0ecb81";
const DOWN = "#f6465d";

function toTime(t: number): UTCTimestamp {
  return ((t + 1) * SECONDS_PER_DAY) as UTCTimestamp;
}

function toDayIndex(time: number): number {
  return Math.round(time / SECONDS_PER_DAY) - 1;
}

function candlePoint(c: Candle) {
  return { time: toTime(c.t), open: c.open, high: c.high, low: c.low, close: c.close };
}

function volumePoint(c: Candle) {
  return {
    time: toTime(c.t),
    value: c.volume,
    color: c.close >= c.open ? "rgba(14,203,129,0.35)" : "rgba(246,70,93,0.35)",
  };
}

export interface ChartHandle {
  reveal: (future: Candle[], onDone: () => void) => void;
}

interface ChartProps {
  visible: Candle[];
  startClose: number;
  horizonDays: number;
}

const Chart = forwardRef<ChartHandle, ChartProps>(function Chart(
  { visible, startClose, horizonDays },
  ref
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const priceLineRef = useRef<IPriceLine | null>(null);
  const timerRef = useRef<number | null>(null);

  // Create the chart once.
  useEffect(() => {
    const container = containerRef.current!;
    const chart = createChart(container, {
      width: container.clientWidth,
      height: container.clientHeight,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#8b96a8",
        fontFamily: "'JetBrains Mono', 'Roboto Mono', monospace",
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.04)" },
        horzLines: { color: "rgba(255,255,255,0.04)" },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: "rgba(255,255,255,0.08)" },
      timeScale: {
        borderColor: "rgba(255,255,255,0.08)",
        // Relabel the fake timeline as day indices so no real date leaks.
        tickMarkFormatter: (time: number) => `D${toDayIndex(time)}`,
      },
      localization: {
        timeFormatter: (time: number) => `Day ${toDayIndex(time)}`,
      },
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: UP,
      downColor: DOWN,
      borderVisible: false,
      wickUpColor: UP,
      wickDownColor: DOWN,
    });

    const volumeSeries = chart.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "",
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.82, bottom: 0 },
    });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    volumeSeriesRef.current = volumeSeries;

    const onResize = () =>
      chart.applyOptions({
        width: container.clientWidth,
        height: container.clientHeight,
      });
    window.addEventListener("resize", onResize);

    return () => {
      window.removeEventListener("resize", onResize);
      if (timerRef.current) window.clearInterval(timerRef.current);
      chart.remove();
    };
  }, []);

  // Reset to the new round's visible window whenever it changes.
  useEffect(() => {
    const chart = chartRef.current;
    const candleSeries = candleSeriesRef.current;
    const volumeSeries = volumeSeriesRef.current;
    if (!chart || !candleSeries || !volumeSeries || visible.length === 0) return;

    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }

    candleSeries.setData(visible.map(candlePoint));
    volumeSeries.setData(visible.map(volumePoint));
    candleSeries.setMarkers([
      {
        time: toTime(visible[visible.length - 1].t),
        position: "aboveBar",
        color: "#f0b90b",
        shape: "arrowDown",
        text: "PREDICT",
      },
    ]);

    if (priceLineRef.current) candleSeries.removePriceLine(priceLineRef.current);
    priceLineRef.current = candleSeries.createPriceLine({
      price: startClose,
      color: "#f0b90b",
      lineWidth: 1,
      lineStyle: 2,
      axisLabelVisible: true,
      title: "entry",
    });

    chart.timeScale().fitContent();
  }, [visible, startClose]);

  useImperativeHandle(ref, () => ({
    reveal(future, onDone) {
      const candleSeries = candleSeriesRef.current;
      const volumeSeries = volumeSeriesRef.current;
      const chart = chartRef.current;
      if (!candleSeries || !volumeSeries || !chart) return;

      candleSeries.setMarkers([]);
      let i = 0;
      timerRef.current = window.setInterval(() => {
        if (i >= future.length) {
          window.clearInterval(timerRef.current!);
          timerRef.current = null;
          const last = future[future.length - 1];
          const up = last.close >= startClose;
          candleSeries.setMarkers([
            {
              time: toTime(last.t),
              position: up ? "aboveBar" : "belowBar",
              color: up ? UP : DOWN,
              shape: up ? "arrowUp" : "arrowDown",
              text: `${up ? "+" : ""}${(
                ((last.close - startClose) / startClose) *
                100
              ).toFixed(1)}%`,
            },
          ]);
          onDone();
          return;
        }
        const c = future[i];
        candleSeries.update(candlePoint(c));
        volumeSeries.update(volumePoint(c));
        chart.timeScale().scrollToPosition(2, false);
        i += 1;
      }, REVEAL_INTERVAL_MS);
    },
  }));

  return (
    <div className="chart-wrap">
      <div className="chart-horizon-badge">
        forecast horizon: <b>{horizonDays} trading days</b>
      </div>
      <div ref={containerRef} className="chart-canvas" />
    </div>
  );
});

export default Chart;
