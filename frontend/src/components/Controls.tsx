import type { MarketState } from "@/lib/types";

export function Controls({
  hour,
  marketState,
  isAdvancing,
  autoPlay,
  error,
  onAdvance,
  onToggleAutoPlay,
}: {
  hour: number;
  marketState: MarketState | null;
  isAdvancing: boolean;
  autoPlay: boolean;
  error: string | null;
  onAdvance: () => void;
  onToggleAutoPlay: () => void;
}) {
  return (
    <header className="flex flex-wrap items-center justify-between gap-4 rounded-lg border p-4" style={{ borderColor: "var(--border)", background: "var(--surface)" }}>
      <div>
        <h1 className="text-lg font-semibold" style={{ color: "var(--foreground)" }}>
          WattShare
        </h1>
        <p className="text-xs" style={{ color: "var(--foreground-muted)" }}>
          Peer-to-peer solar trading dispatcher
        </p>
      </div>

      <div className="flex items-center gap-3">
        <div className="text-sm tabular-nums" style={{ color: "var(--foreground-secondary)" }}>
          Hour <span className="font-semibold" style={{ color: "var(--foreground)" }}>{String(hour).padStart(2, "0")}:00</span>
        </div>

        {marketState && marketState.clearing_price !== null && (
          <div className="text-xs tabular-nums" style={{ color: "var(--foreground-muted)" }}>
            supply {marketState.total_supply_kwh.toFixed(1)} kWh &middot; demand {marketState.total_demand_kwh.toFixed(1)} kWh
          </div>
        )}

        {error && (
          <span className="text-xs" style={{ color: "var(--status-critical)" }}>
            {error}
          </span>
        )}

        <button
          onClick={onAdvance}
          disabled={isAdvancing || autoPlay}
          className="rounded-md px-3 py-1.5 text-sm font-medium text-white transition-opacity disabled:opacity-50"
          style={{ background: "var(--series-generation)" }}
        >
          {isAdvancing ? "Advancing..." : "Advance Hour"}
        </button>

        <button
          onClick={onToggleAutoPlay}
          className="rounded-md border px-3 py-1.5 text-sm font-medium"
          style={{ borderColor: "var(--border)", color: "var(--foreground)" }}
        >
          {autoPlay ? "Stop" : "Auto-play"}
        </button>
      </div>
    </header>
  );
}
