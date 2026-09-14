import { BoltIcon } from "./icons";

export function Header({ householdCount }: { householdCount: number }) {
  return (
    <header className="flex items-center justify-between gap-4">
      <div className="flex items-center gap-3">
        <span
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full"
          style={{ background: "var(--strong)", color: "var(--strong-contrast)" }}
        >
          <BoltIcon />
        </span>
        <div>
          <h1 className="text-lg font-semibold leading-tight" style={{ color: "var(--ink)" }}>
            WattShare
          </h1>
          <p className="text-xs" style={{ color: "var(--ink-muted)" }}>
            Neighborhood dispatcher
          </p>
        </div>
      </div>

      <div
        className="hidden items-center gap-2 rounded-full py-1.5 pl-1.5 pr-4 sm:flex"
        style={{ background: "var(--card-bg)" }}
      >
        <span
          className="flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold"
          style={{ background: "var(--accent-soft)", color: "var(--accent)" }}
        >
          {householdCount}
        </span>
        <div className="leading-tight">
          <p className="text-xs font-medium" style={{ color: "var(--ink)" }}>
            Households
          </p>
          <p className="text-[11px]" style={{ color: "var(--ink-muted)" }}>
            Simulated microgrid
          </p>
        </div>
      </div>
    </header>
  );
}
