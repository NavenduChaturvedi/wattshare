"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card } from "./Card";

export interface PricePoint {
  hour: number;
  price: number;
}

export function PriceChart({ data }: { data: PricePoint[] }) {
  return (
    <Card title="Clearing Price" subtitle="Rs/kWh, since page load -- dashed lines mark the price floor/ceiling">
      <div className="h-56">
        {data.length === 0 ? (
          <EmptyState message="Run the market to see the clearing price." />
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
              <CartesianGrid stroke="var(--grid-line)" vertical={false} />
              <XAxis
                dataKey="hour"
                tickFormatter={(h: number) => `${String(h).padStart(2, "0")}:00`}
                stroke="var(--foreground-muted)"
                fontSize={11}
                tickLine={false}
              />
              <YAxis
                domain={[3, 13]}
                stroke="var(--foreground-muted)"
                fontSize={11}
                tickLine={false}
                width={32}
              />
              <ReferenceLine y={4} stroke="var(--foreground-muted)" strokeDasharray="3 3" />
              <ReferenceLine y={12} stroke="var(--foreground-muted)" strokeDasharray="3 3" />
              <Tooltip
                contentStyle={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: 6,
                  fontSize: 12,
                }}
                labelFormatter={(h) => `Hour ${String(h).padStart(2, "0")}:00`}
                formatter={(value) => [`Rs ${Number(value).toFixed(2)}/kWh`, "Clearing price"]}
              />
              <Line
                type="monotone"
                dataKey="price"
                stroke="var(--series-price)"
                strokeWidth={2}
                strokeLinecap="round"
                dot={{ r: 3, fill: "var(--series-price)", strokeWidth: 0 }}
                activeDot={{ r: 5 }}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </Card>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex h-full items-center justify-center text-sm" style={{ color: "var(--foreground-muted)" }}>
      {message}
    </div>
  );
}
