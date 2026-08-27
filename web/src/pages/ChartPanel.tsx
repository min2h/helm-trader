import { ColorType, createChart, type UTCTimestamp } from "lightweight-charts";
import { useEffect, useRef } from "react";

type Bar = { time: number; open: number; high: number; low: number; close: number };

export function ChartPanel({
  bars,
  lower,
  upper,
}: {
  bars: Bar[];
  lower?: number;
  upper?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = createChart(ref.current, {
      height: 360,
      layout: {
        background: { type: ColorType.Solid, color: "#1d1913" },
        textColor: "#9a8b73",
      },
      grid: { vertLines: { color: "#2a241c" }, horzLines: { color: "#2a241c" } },
      rightPriceScale: { borderColor: "#3a3226" },
      timeScale: { borderColor: "#3a3226" },
    });
    const series = chart.addCandlestickSeries({
      upColor: "#c4a574",
      downColor: "#c45c3e",
      wickUpColor: "#c4a574",
      wickDownColor: "#c45c3e",
      borderVisible: false,
    });
    series.setData(bars.map((bar) => ({ ...bar, time: bar.time as UTCTimestamp })));
    if (lower) series.createPriceLine({ price: lower, color: "#c45c3e", lineStyle: 2, title: "하한" });
    if (upper) series.createPriceLine({ price: upper, color: "#7d9a6a", lineStyle: 2, title: "상한" });
    chart.timeScale().fitContent();
    const observer = new ResizeObserver(() => chart.applyOptions({ width: ref.current?.clientWidth }));
    observer.observe(ref.current);
    return () => {
      observer.disconnect();
      chart.remove();
    };
  }, [bars, lower, upper]);

  return <div className="chart" ref={ref} />;
}
