"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Household } from "@/lib/types";
import { Card } from "./Card";
import { SunIcon } from "./icons";

export function GenerationChart({ households }: { households: Household[] }) {
  const data = households.map((h) => ({
    id: h.id,
    generation: h.current_generation_kwh,
    consumption: h.current_consumption_kwh,
  }));

  return (
    <Card
      title="Generation vs. Consumption"
      subtitle="Per household, this hour (kWh)"
      icon={<SunIcon className="h-4 w-4" />}
    >
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -4 }}>
            <CartesianGrid stroke="var(--grid-line)" vertical={false} />
            <XAxis dataKey="id" stroke="var(--ink-muted)" fontSize={11} tickLine={false} />
            {/* Real-data ticks are fractional kWh (0.25, 0.5...): up to two decimals, trailing zeros dropped. */}
            <YAxis
              stroke="var(--ink-muted)"
              fontSize={11}
              tickLine={false}
              width={36}
              tickFormatter={(v: number) => String(Number(v.toFixed(2)))}
            />
            <Tooltip
              contentStyle={{
                background: "var(--card-bg)",
                border: "1px solid var(--border)",
                borderRadius: 10,
                fontSize: 12,
              }}
              formatter={(value) => `${Number(value).toFixed(2)} kWh`}
            />
            <Legend
              wrapperStyle={{ fontSize: 12, color: "var(--ink-secondary)" }}
              iconType="circle"
              iconSize={8}
            />
            <Bar dataKey="generation" name="Generation" fill="var(--series-generation)" radius={[3, 3, 0, 0]} />
            <Bar dataKey="consumption" name="Consumption" fill="var(--series-consumption)" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
