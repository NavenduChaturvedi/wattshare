export function StatTile({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-3xl p-5" style={{ background: "var(--card-bg)" }}>
      <p className="text-xs font-medium" style={{ color: "var(--ink-muted)" }}>
        {label}
      </p>
      <p className="mt-1 text-2xl font-bold tabular-nums" style={{ color: "var(--ink)" }}>
        {value}
      </p>
      {hint && (
        <p className="mt-1 text-xs" style={{ color: "var(--ink-secondary)" }}>
          {hint}
        </p>
      )}
    </div>
  );
}
