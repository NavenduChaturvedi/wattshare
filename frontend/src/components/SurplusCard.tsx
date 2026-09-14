"use client";

import { useState } from "react";
import type { Listing, PricingMode } from "@/lib/types";
import { Card } from "./Card";
import { SunIcon } from "./icons";

/**
 * Keyed by the parent on `listing?.id` (see seller/page.tsx) so this remounts --
 * resetting its local draft state from props via the lazy initializers below --
 * exactly when the listing identity actually changes (a fresh fetch, or the new
 * row our own save just created), rather than syncing state from props in an effect.
 */
export function SurplusCard({
  householdName,
  currentSurplusKwh,
  listing,
  defaultPrice,
  onSave,
  saving,
  error,
}: {
  householdName: string;
  currentSurplusKwh: number;
  listing: Listing | null;
  defaultPrice: number;
  onSave: (mode: PricingMode, price: number | null) => void;
  saving: boolean;
  error: string | null;
}) {
  const [mode, setMode] = useState<PricingMode>(() => listing?.pricing_mode ?? "auto");
  const [price, setPrice] = useState(() => (listing?.asking_price_per_kwh ?? defaultPrice).toFixed(1));

  function selectMode(next: PricingMode) {
    setMode(next);
    onSave(next, next === "manual" ? Number(price) || defaultPrice : null);
  }

  function submitPrice(e: React.FormEvent) {
    e.preventDefault();
    const parsed = Number(price);
    if (parsed > 0) onSave("manual", parsed);
  }

  return (
    <Card title={`${householdName || "..."}'s Surplus`} subtitle="Live from the simulation" icon={<SunIcon className="h-4 w-4" />}>
      <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-3xl font-bold tabular-nums" style={{ color: "var(--ink)" }}>
            {currentSurplusKwh.toFixed(2)}
            <span className="ml-1 text-base font-medium" style={{ color: "var(--ink-muted)" }}>
              kWh
            </span>
          </p>
          <p className="text-xs" style={{ color: "var(--ink-muted)" }}>available to sell right now</p>
        </div>

        <div className="flex flex-col items-start gap-2">
          <div className="inline-flex rounded-full p-1" style={{ background: "var(--panel-bg)" }}>
            <button
              onClick={() => selectMode("auto")}
              className="rounded-full px-3 py-1.5 text-xs font-medium transition-colors"
              style={mode === "auto" ? { background: "var(--accent)", color: "var(--accent-contrast)" } : { color: "var(--ink)" }}
            >
              Auto-sell at market price
            </button>
            <button
              onClick={() => selectMode("manual")}
              className="rounded-full px-3 py-1.5 text-xs font-medium transition-colors"
              style={mode === "manual" ? { background: "var(--accent)", color: "var(--accent-contrast)" } : { color: "var(--ink)" }}
            >
              Set my own price
            </button>
          </div>

          {mode === "manual" && (
            <form onSubmit={submitPrice} className="flex items-center gap-2">
              <span className="text-xs" style={{ color: "var(--ink-muted)" }}>
                Rs
              </span>
              <input
                type="number"
                step="0.1"
                min="0.1"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                className="w-20 rounded-full border px-3 py-1 text-sm tabular-nums"
                style={{ borderColor: "var(--border)", background: "var(--card-bg)", color: "var(--ink)" }}
              />
              <span className="text-xs" style={{ color: "var(--ink-muted)" }}>
                /kWh
              </span>
              <button
                type="submit"
                disabled={saving}
                className="rounded-full px-3 py-1 text-xs font-medium disabled:opacity-50"
                style={{ background: "var(--strong)", color: "var(--strong-contrast)" }}
              >
                {saving ? "Saving..." : "Update"}
              </button>
            </form>
          )}
        </div>
      </div>

      {error && (
        <p className="mt-3 text-xs" style={{ color: "var(--status-critical)" }}>
          {error}
        </p>
      )}
    </Card>
  );
}
