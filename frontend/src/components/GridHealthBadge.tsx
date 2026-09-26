import type { GridHealth } from "@/lib/types";

const CONFIG: Record<GridHealth, { label: string; bg: string; fg: string }> = {
  green: { label: "Grid healthy", bg: "var(--status-good-soft)", fg: "var(--status-good)" },
  yellow: { label: "Grid moderate", bg: "var(--accent-soft)", fg: "var(--accent)" },
  red: { label: "Grid stressed", bg: "var(--status-critical-soft)", fg: "var(--status-critical)" },
};

export function GridHealthBadge({ health, loadPct }: { health: GridHealth; loadPct?: number | null }) {
  const cfg = CONFIG[health];
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium"
      style={{ background: cfg.bg, color: cfg.fg }}
    >
      <span className="h-2 w-2 rounded-full" style={{ background: cfg.fg }} aria-hidden />
      {cfg.label}
      {loadPct != null && (
        <span className="font-normal tabular-nums" title="Transformer load, % of rated capacity">
          &middot; transformer {Math.round(loadPct)}%
        </span>
      )}
    </span>
  );
}
