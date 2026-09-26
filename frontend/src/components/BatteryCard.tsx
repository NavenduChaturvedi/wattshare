import type { Household } from "@/lib/types";
import { Card } from "./Card";
import { BoltIcon } from "./icons";

function status(flow: number): { label: string; detail: string } {
  if (flow > 0.005) return { label: "Charging", detail: "Storing your solar while local energy is cheap" };
  if (flow < -0.005) return { label: "Releasing", detail: "Covering your load first, then selling the rest" };
  return { label: "Holding", detail: "Saving its charge for a pricier hour" };
}

export function BatteryCard({ household }: { household: Household }) {
  const capacity = household.battery_capacity_kwh;
  const stored = household.battery_stored_kwh;
  const pct = capacity > 0 ? Math.round((stored / capacity) * 100) : 0;
  const flow = household.battery_flow_kwh;
  const s = status(flow);

  return (
    <Card title="Home Battery" subtitle={s.detail} icon={<BoltIcon className="h-4 w-4" />}>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-3xl font-bold tabular-nums" style={{ color: "var(--ink)" }}>
            {stored.toFixed(1)}
            <span className="ml-1 text-base font-medium" style={{ color: "var(--ink-muted)" }}>
              / {capacity.toFixed(1)} kWh
            </span>
          </p>
          <p className="text-xs" style={{ color: "var(--ink-muted)" }}>
            stored ({pct}%)
          </p>
        </div>
        <span
          className="rounded-full px-3 py-1 text-xs font-medium tabular-nums"
          style={
            flow < -0.005
              ? { background: "var(--status-good-soft)", color: "var(--status-good)" }
              : flow > 0.005
                ? { background: "var(--accent-soft)", color: "var(--accent)" }
                : { background: "var(--panel-bg)", color: "var(--ink-muted)" }
          }
        >
          {s.label}
          {Math.abs(flow) > 0.005 && ` ${Math.abs(flow).toFixed(1)} kWh this hour`}
        </span>
      </div>
      <div
        className="mt-4 h-2.5 w-full overflow-hidden rounded-full"
        style={{ background: "var(--panel-bg)" }}
        role="meter"
        aria-label="Battery charge"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={pct}
      >
        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: "var(--status-good)" }} />
      </div>
    </Card>
  );
}
