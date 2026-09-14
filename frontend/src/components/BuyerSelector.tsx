import type { Household } from "@/lib/types";

export function BuyerSelector({
  households,
  selectedId,
  onSelect,
}: {
  households: Household[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-3xl p-3" style={{ background: "var(--card-bg)" }}>
      <span className="pl-2 text-xs font-medium" style={{ color: "var(--ink-muted)" }}>
        Buying as
      </span>
      <select
        value={selectedId ?? ""}
        onChange={(e) => onSelect(e.target.value)}
        className="rounded-full border px-3 py-1.5 text-sm font-medium"
        style={{ borderColor: "var(--border)", background: "var(--panel-bg)", color: "var(--ink)" }}
      >
        {households.map((h) => (
          <option key={h.id} value={h.id}>
            {h.name} &middot; {h.zone_id}
          </option>
        ))}
      </select>
    </div>
  );
}
