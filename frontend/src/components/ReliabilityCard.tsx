import { Card } from "./Card";
import { ShieldIcon } from "./icons";

export function ReliabilityCard({ score }: { score: number | null }) {
  const pct = score !== null ? Math.round(score * 100) : null;
  const tier = pct === null ? "neutral" : pct >= 80 ? "good" : pct >= 60 ? "ok" : "poor";

  const style =
    tier === "good"
      ? { bg: "var(--status-good-soft)", fg: "var(--status-good)" }
      : tier === "poor"
        ? { bg: "var(--status-critical-soft)", fg: "var(--status-critical)" }
        : tier === "ok"
          ? { bg: "var(--accent-soft)", fg: "var(--accent)" }
          : { bg: "var(--panel-bg)", fg: "var(--ink-muted)" };

  const label =
    pct === null ? "Loading..." : pct >= 80 ? "Reliable seller" : pct >= 60 ? "Building history" : "Needs improvement";

  return (
    <Card title="Reliability" subtitle="Fulfillment rate, not a star rating" icon={<ShieldIcon className="h-4 w-4" />}>
      <div className="flex flex-col items-center justify-center gap-2 py-2">
        <div
          className="flex h-24 w-24 items-center justify-center rounded-full text-2xl font-bold tabular-nums"
          style={{ background: style.bg, color: style.fg }}
        >
          {pct !== null ? `${pct}%` : "--"}
        </div>
        <p className="text-center text-xs" style={{ color: "var(--ink-muted)" }}>
          {label}
        </p>
      </div>
    </Card>
  );
}
