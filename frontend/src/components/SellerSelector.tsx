import type { Household } from "@/lib/types";

export function SellerSelector({
  households,
  selectedId,
  onSelect,
}: {
  households: Household[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-3xl p-3" style={{ background: "var(--card-bg)" }}>
      <span className="pl-2 text-xs font-medium" style={{ color: "var(--ink-muted)" }}>
        Viewing as
      </span>
      {households.map((h) => {
        const active = h.id === selectedId;
        return (
          <button
            key={h.id}
            onClick={() => onSelect(h.id)}
            className="rounded-full px-3 py-1.5 text-sm font-medium transition-colors"
            style={active ? { background: "var(--strong)", color: "var(--strong-contrast)" } : { background: "var(--panel-bg)", color: "var(--ink)" }}
          >
            {h.name}
          </button>
        );
      })}
    </div>
  );
}
