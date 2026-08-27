import { ColorType, createChart, type UTCTimestamp } from "lightweight-charts";
import { useEffect, useRef } from "react";

type Bar = { time: number; open: number; high: number; low: number; close: number };

export function ChartPanel({
  bars,
  lower,
  upper,
  light = false,
}: {
  bars: Bar[];
  lower?: number;
  upper?: number;
  light?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    const fitHeight = (width: number) => Math.max(240, Math.min(420, Math.round(width * 0.62)));
    const chart = createChart(ref.current, {
      height: fitHeight(ref.current.clientWidth),
      localization: {
        priceFormatter: (price: number) =>
          `$${price.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
      },
      layout: {
        background: { type: ColorType.Solid, color: light ? "#ffffff" : "#151b23" },
        textColor: light ? "#667588" : "#8b97a6",
      },
      grid: {
        vertLines: { color: light ? "#e6edf5" : "#2a3544" },
        horzLines: { color: light ? "#e6edf5" : "#2a3544" },
      },
      rightPriceScale: { borderColor: light ? "#d5dee8" : "#2a3544" },
      timeScale: { borderColor: light ? "#d5dee8" : "#2a3544" },
    });
    const series = chart.addCandlestickSeries({
      upColor: "#3dcb8a",
      downColor: "#ef6b5c",
      wickUpColor: "#3dcb8a",
      wickDownColor: "#ef6b5c",
      borderVisible: false,
    });
    series.setData(bars.map((bar) => ({ ...bar, time: bar.time as UTCTimestamp })));
    if (lower) series.createPriceLine({ price: lower, color: "#ef6b5c", lineStyle: 2, title: "하한" });
    if (upper) series.createPriceLine({ price: upper, color: "#3dcb8a", lineStyle: 2, title: "상한" });
    chart.timeScale().fitContent();
    const observer = new ResizeObserver(() => {
      const width = ref.current?.clientWidth;
      if (!width) return;
      chart.applyOptions({ width, height: fitHeight(width) });
    });
    observer.observe(ref.current);
    return () => {
      observer.disconnect();
      chart.remove();
    };
  }, [bars, lower, upper, light]);

  return <div className="chart" ref={ref} />;
}
