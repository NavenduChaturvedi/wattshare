"use client";

import { useState } from "react";
import type { BuyerListing } from "@/lib/types";
import { Card } from "./Card";
import { TagIcon } from "./icons";

function ProximityChip({ sameZone }: { sameZone: boolean }) {
  return (
    <span
      className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
      style={
        sameZone
          ? { background: "var(--status-good-soft)", color: "var(--status-good)" }
          : { background: "var(--panel-bg)", color: "var(--ink-muted)" }
      }
    >
      {sameZone ? "Same block" : "Nearby"}
    </span>
  );
}

function ReliabilityChip({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const style =
    pct >= 80
      ? { bg: "var(--status-good-soft)", fg: "var(--status-good)" }
      : pct >= 60
        ? { bg: "var(--accent-soft)", fg: "var(--accent)" }
        : { bg: "var(--status-critical-soft)", fg: "var(--status-critical)" };
  return (
    <span className="inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium tabular-nums" style={{ background: style.bg, color: style.fg }}>
      {pct}%
    </span>
  );
}

interface RowResult {
  message: string;
  success: boolean;
}

export function ListingTable({
  listings,
  myZoneId,
  myNeedKwh,
  onBuy,
}: {
  listings: BuyerListing[];
  myZoneId: string | null;
  myNeedKwh: number;
  onBuy: (listing: BuyerListing) => Promise<RowResult>;
}) {
  // Keyed by seller, not listing id: every sale re-snapshots the listing under a new id,
  // so an id-keyed result would vanish the moment the table reloads after the purchase.
  const [loadingSeller, setLoadingSeller] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, RowResult>>({});

  async function handleBuy(listing: BuyerListing) {
    setLoadingSeller(listing.seller_household_id);
    setResults((prev) => {
      const next = { ...prev };
      delete next[listing.seller_household_id];
      return next;
    });
    const result = await onBuy(listing);
    setResults((prev) => ({ ...prev, [listing.seller_household_id]: result }));
    setLoadingSeller(null);
  }

  return (
    <Card title="Available Sellers" subtitle={`${listings.length} active listing(s)`} icon={<TagIcon className="h-4 w-4" />}>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr style={{ color: "var(--ink-muted)" }}>
              <th className="pb-2 font-medium">Seller</th>
              <th className="pb-2 font-medium">Zone</th>
              <th className="pb-2 pr-2 text-right font-medium">Available</th>
              <th className="pb-2 pr-2 text-right font-medium">Price</th>
              <th className="pb-2 pr-2 text-right font-medium">Reliability</th>
              <th className="pb-2 text-right font-medium">&nbsp;</th>
            </tr>
          </thead>
          <tbody className="tabular-nums" style={{ color: "var(--ink)" }}>
            {listings.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-6 text-center" style={{ color: "var(--ink-muted)" }}>
                  No sellers listed right now -- check back after the next hour.
                </td>
              </tr>
            ) : (
              listings.map((l) => (
                <tr key={l.id} className="border-t" style={{ borderColor: "var(--grid-line)" }}>
                  <td className="py-2">{l.seller_name}</td>
                  <td className="py-2">
                    <ProximityChip sameZone={l.zone_id === myZoneId} />
                  </td>
                  <td className="py-2 pr-2 text-right">{l.units_available_kwh.toFixed(2)} kWh</td>
                  <td className="py-2 pr-2 text-right font-medium">Rs {l.price_per_kwh.toFixed(2)}</td>
                  <td className="py-2 pr-2 text-right">
                    <ReliabilityChip score={l.reliability_score} />
                  </td>
                  <td className="py-2 text-right align-top">
                    <button
                      onClick={() => handleBuy(l)}
                      disabled={loadingSeller === l.seller_household_id || myNeedKwh <= 0}
                      title={myNeedKwh <= 0 ? "This household has no deficit to cover this hour" : undefined}
                      className="rounded-full px-3 py-1 text-xs font-medium disabled:opacity-50"
                      style={{ background: "var(--strong)", color: "var(--strong-contrast)" }}
                    >
                      {loadingSeller === l.seller_household_id
                        ? "Buying..."
                        : myNeedKwh <= 0
                          ? "Nothing needed"
                          : `Buy ${Math.min(l.units_available_kwh, myNeedKwh).toFixed(2)} kWh`}
                    </button>
                    {results[l.seller_household_id] && (
                      <p
                        className="mt-1 max-w-[16rem] text-right text-xs font-normal normal-case"
                        style={{ color: results[l.seller_household_id].success ? "var(--status-good)" : "var(--status-critical)" }}
                      >
                        {results[l.seller_household_id].message}
                      </p>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      {/* A purchase that sells a listing out removes its row -- keep the confirmation visible. */}
      {Object.entries(results)
        .filter(([sellerId]) => !listings.some((l) => l.seller_household_id === sellerId))
        .map(([sellerId, r]) => (
          <p
            key={sellerId}
            className="mt-3 text-xs"
            style={{ color: r.success ? "var(--status-good)" : "var(--status-critical)" }}
          >
            {r.message}
          </p>
        ))}
    </Card>
  );
}
