"use client";

import { useState } from "react";
import type { SmartMatchResult } from "@/lib/types";
import { Card } from "./Card";
import { BoltIcon } from "./icons";

export function SmartMatchCard({
  buyerId,
  onRun,
}: {
  buyerId: string | null;
  onRun: (desiredKwh: number) => Promise<SmartMatchResult>;
}) {
  const [desiredKwh, setDesiredKwh] = useState("2.0");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SmartMatchResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    const parsed = Number(desiredKwh);
    if (!buyerId || !(parsed > 0)) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await onRun(parsed);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Smart Match failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card
      title="Smart Match"
      subtitle="Enter how much you need -- the dispatcher finds your best deal automatically"
      icon={<BoltIcon className="h-4 w-4" />}
    >
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <input
            type="number"
            step="0.1"
            min="0.1"
            value={desiredKwh}
            onChange={(e) => setDesiredKwh(e.target.value)}
            className="w-24 rounded-full border px-3 py-1.5 text-sm tabular-nums"
            style={{ borderColor: "var(--border)", background: "var(--panel-bg)", color: "var(--ink)" }}
          />
          <span className="text-sm" style={{ color: "var(--ink-muted)" }}>
            kWh needed
          </span>
        </div>
        <button
          onClick={handleClick}
          disabled={loading || !buyerId}
          className="rounded-full px-4 py-2 text-sm font-medium disabled:opacity-50"
          style={{ background: "var(--accent)", color: "var(--accent-contrast)" }}
        >
          {loading ? "Matching..." : "Smart Match"}
        </button>
      </div>

      {error && (
        <p className="mt-3 text-sm font-medium" style={{ color: "var(--status-critical)" }}>
          {error}
        </p>
      )}

      {result && (
        <div className="mt-4 rounded-2xl p-4" style={{ background: result.fully_matched ? "var(--status-good-soft)" : "var(--accent-soft)" }}>
          <p className="font-semibold" style={{ color: result.fully_matched ? "var(--status-good)" : "var(--accent)" }}>
            {result.fully_matched ? "Fully matched" : "Partially matched -- not enough supply right now"}
          </p>
          <p className="text-sm tabular-nums" style={{ color: "var(--ink)" }}>
            {result.total_kwh_matched.toFixed(2)} kWh for Rs {result.total_cost.toFixed(2)} total
          </p>
          {result.trades.length > 0 && (
            <ul className="mt-2 space-y-0.5 text-sm tabular-nums" style={{ color: "var(--ink-secondary)" }}>
              {result.trades.map((t) => (
                <li key={t.id}>
                  {t.seller_id} &rarr; {t.amount_kwh.toFixed(2)} kWh @ Rs {t.price_per_kwh.toFixed(2)}/kWh
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </Card>
  );
}
