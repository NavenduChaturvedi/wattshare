"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { SimConfig } from "@/lib/types";
import { BoltIcon } from "./icons";

const NAV_LINKS = [
  { href: "/", label: "Dispatcher" },
  { href: "/seller", label: "Seller" },
  { href: "/buyer", label: "Buyer" },
];

function provenanceLine(config: SimConfig | null): string {
  if (!config) return "Neighborhood dispatcher";
  if (config.data_source === "synthetic") return "Synthetic data";
  const day = new Date(`${config.sim_date}T00:00:00`).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
  return `${config.location} · ${day} · real weather & load data`;
}

export function Header({ householdCount, config }: { householdCount: number; config: SimConfig | null }) {
  const pathname = usePathname();

  return (
    <header className="flex flex-wrap items-center justify-between gap-4">
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
          <p
            className="text-xs"
            style={{ color: "var(--ink-muted)" }}
            title={config ? `Solar: ${config.solar_source}
Load: ${config.load_source}` : undefined}
          >
            {provenanceLine(config)}
          </p>
        </div>
      </div>

      <nav className="flex items-center gap-1 rounded-full p-1" style={{ background: "var(--card-bg)" }}>
        {NAV_LINKS.map((link) => {
          const active = pathname === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              className="rounded-full px-3 py-1.5 text-sm font-medium transition-colors"
              style={active ? { background: "var(--accent)", color: "var(--accent-contrast)" } : { color: "var(--ink-secondary)" }}
            >
              {link.label}
            </Link>
          );
        })}
      </nav>

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
