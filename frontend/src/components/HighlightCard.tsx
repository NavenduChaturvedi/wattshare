import type { BuyerListing } from "@/lib/types";

export function HighlightCard({
  label,
  listing,
  metric,
  icon,
}: {
  label: string;
  listing: BuyerListing | null;
  metric: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-3 rounded-3xl p-5" style={{ background: "var(--card-bg)" }}>
      <span
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full"
        style={{ background: "var(--accent-soft)", color: "var(--accent)" }}
      >
        {icon}
      </span>
      <div>
        <p className="text-xs font-medium" style={{ color: "var(--ink-muted)" }}>
          {label}
        </p>
        {listing ? (
          <>
            <p className="text-lg font-bold" style={{ color: "var(--ink)" }}>
              {listing.seller_name}
            </p>
            <p className="text-sm tabular-nums" style={{ color: "var(--accent)" }}>
              {metric}
            </p>
          </>
        ) : (
          <p className="mt-0.5 text-sm" style={{ color: "var(--ink-muted)" }}>
            No listings yet
          </p>
        )}
      </div>
    </div>
  );
}
