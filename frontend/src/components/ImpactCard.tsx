import { Card } from "./Card";
import { LeafIcon } from "./icons";

// Rough grid-displacement estimate (kg CO2 avoided per kWh of solar sold instead of
// drawn from the grid). Not scientifically rigorous -- a motivational stat, labeled
// as an estimate per the spec.
const CO2_KG_PER_KWH = 0.7;

export function ImpactCard({ totalKwhSold }: { totalKwhSold: number }) {
  const co2Avoided = totalKwhSold * CO2_KG_PER_KWH;

  return (
    <Card title="Your Impact" subtitle="Estimated -- a motivational stat, not a certified offset" icon={<LeafIcon className="h-4 w-4" />}>
      <div className="grid grid-cols-2 gap-6">
        <div>
          <p className="text-2xl font-bold tabular-nums" style={{ color: "var(--ink)" }}>
            {totalKwhSold.toFixed(1)} <span className="text-sm font-medium" style={{ color: "var(--ink-muted)" }}>kWh</span>
          </p>
          <p className="text-xs" style={{ color: "var(--ink-muted)" }}>sold lifetime</p>
        </div>
        <div>
          <p className="text-2xl font-bold tabular-nums" style={{ color: "var(--accent)" }}>
            ~{co2Avoided.toFixed(1)} <span className="text-sm font-medium" style={{ color: "var(--ink-muted)" }}>kg CO&#8322;</span>
          </p>
          <p className="text-xs" style={{ color: "var(--ink-muted)" }}>estimated offset</p>
        </div>
      </div>
    </Card>
  );
}
