import type { MarketSummary } from "@/lib/types";
import { GridHealthBadge } from "./GridHealthBadge";

export function MarketPulse({ summary }: { summary: MarketSummary | null }) {
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-3xl p-4" style={{ background: "var(--card-bg)" }}>
      {summary ? (
        <GridHealthBadge health={summary.grid_health} loadPct={summary.transformer_load_pct} />
      ) : (
        <span className="text-sm" style={{ color: "var(--ink-muted)" }}>
          Loading grid status...
        </span>
      )}
      {summary?.average_listing_price != null && (
        <span className="text-sm" style={{ color: "var(--ink-secondary)" }}>
          Market average:{" "}
          <strong className="tabular-nums" style={{ color: "var(--ink)" }}>
            Rs {summary.average_listing_price.toFixed(2)}/kWh
          </strong>
        </span>
      )}
    </div>
  );
}
