"use client";

import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis } from "recharts";
import type { MarketTrendPoint } from "@/lib/types";
import { Card } from "./Card";
import { TrendIcon } from "./icons";

export function PriceSparkline({ points }: { points: MarketTrendPoint[] }) {
  const first = points[0];
  const last = points[points.length - 1];
  const delta = first && last ? last.clearing_price - first.clearing_price : 0;
  const pct = first && first.clearing_price > 0 ? (delta / first.clearing_price) * 100 : 0;
  const trendingDown = delta < -0.01;
  const trendingUp = delta > 0.01;

  return (
    <Card title="Today's Price Trend" subtitle="Is now a good time to buy?" icon={<TrendIcon className="h-4 w-4" />}>
      {points.length < 2 ? (
        <p className="py-6 text-center text-sm" style={{ color: "var(--ink-muted)" }}>
          Not enough price history yet -- advance a few more hours.
        </p>
      ) : (
        <>
          <div className="mb-2 flex items-center justify-between">
            <p className="text-2xl font-bold tabular-nums" style={{ color: "var(--ink)" }}>
              Rs {last.clearing_price.toFixed(2)}
              <span className="ml-1 text-sm font-medium" style={{ color: "var(--ink-muted)" }}>
                /kWh now
              </span>
            </p>
            <span
              className="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium tabular-nums"
              style={
                trendingDown
                  ? { background: "var(--status-good-soft)", color: "var(--status-good)" }
                  : trendingUp
                    ? { background: "var(--status-critical-soft)", color: "var(--status-critical)" }
                    : { background: "var(--panel-bg)", color: "var(--ink-muted)" }
              }
            >
              {trendingDown ? "▼" : trendingUp ? "▲" : "—"} {Math.abs(pct).toFixed(0)}% vs this morning
            </span>
          </div>

          <div className="h-16">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={points} margin={{ top: 4, right: 4, bottom: 0, left: 4 }}>
                <defs>
                  <linearGradient id="sparklineFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--series-price)" stopOpacity={0.25} />
                    <stop offset="100%" stopColor="var(--series-price)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                {/* Hidden axis: drives correct x-positioning and tooltip labels without drawing any chrome -- a true sparkline has no visible axes. */}
                <XAxis dataKey="hour" hide />
                <Tooltip
                  contentStyle={{ background: "var(--card-bg)", border: "1px solid var(--border)", borderRadius: 10, fontSize: 12 }}
                  labelFormatter={(h) => `Hour ${String(h).padStart(2, "0")}:00`}
                  formatter={(value) => [`Rs ${Number(value).toFixed(2)}/kWh`, "Price"]}
                />
                <Area
                  type="monotone"
                  dataKey="clearing_price"
                  stroke="var(--series-price)"
                  strokeWidth={2}
                  fill="url(#sparklineFill)"
                  dot={false}
                  activeDot={{ r: 4 }}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </Card>
  );
}
