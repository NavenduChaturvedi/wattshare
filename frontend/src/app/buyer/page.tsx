"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useSimulation } from "@/lib/useSimulation";
import type { BuyerListing, MarketSummary } from "@/lib/types";
import { Header } from "@/components/Header";
import { Hero } from "@/components/Hero";
import { BuyerSelector } from "@/components/BuyerSelector";
import { MarketPulse } from "@/components/MarketPulse";
import { PriceSparkline } from "@/components/PriceSparkline";
import { HighlightCard } from "@/components/HighlightCard";
import { SmartMatchCard } from "@/components/SmartMatchCard";
import { ListingTable } from "@/components/ListingTable";
import { ShieldIcon, TrendIcon } from "@/components/icons";

export default function BuyerPage() {
  const sim = useSimulation();
  const [selectedBuyerId, setSelectedBuyerId] = useState<string | null>(null);
  const buyerId = selectedBuyerId ?? sim.households[0]?.id ?? null;

  const [listings, setListings] = useState<BuyerListing[]>([]);
  const [summary, setSummary] = useState<MarketSummary | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  async function loadMarketData() {
    try {
      // Sequential, not Promise.all -- see seller/page.tsx for why.
      const fetchedListings = await api.getActiveListings();
      setListings(fetchedListings);

      const fetchedSummary = await api.getMarketSummary();
      setSummary(fetchedSummary);
      setLoadError(null);
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "Couldn't load market data");
    }
  }

  const apiReady = sim.connection === "ready";

  useEffect(() => {
    if (!apiReady) return; // don't race the cold-start retry loop in useSimulation
    // loadMarketData's setState calls happen after an await, not synchronously in
    // the effect body -- the standard "fetch on mount/dep-change" pattern.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadMarketData();
  }, [sim.hour, apiReady]);

  const me = sim.households.find((h) => h.id === buyerId) ?? null;
  const myZoneId = me?.zone_id ?? null;
  // What this household still has to cover this hour -- the server caps purchases at it too.
  const myNeedKwh = me ? Math.max(-me.open_net_kwh, 0) : 0;

  // A household doesn't shop its own surplus as a buyer.
  const shoppableListings = listings.filter((l) => l.seller_household_id !== buyerId);

  const bestPriceListing =
    shoppableListings.length > 0
      ? shoppableListings.reduce((best, l) => (l.price_per_kwh < best.price_per_kwh ? l : best))
      : null;
  const mostReliableListing =
    shoppableListings.length > 0
      ? shoppableListings.reduce((best, l) => (l.reliability_score > best.reliability_score ? l : best))
      : null;

  async function handleBuy(listing: BuyerListing, amountKwh: number, maxPricePerKwh: number) {
    if (!buyerId) return { message: "Select a household first.", success: false };
    try {
      const result = await api.buyFromListing(listing.id, buyerId, amountKwh, maxPricePerKwh);
      await sim.refreshHouseholds();
      await loadMarketData();
      return { message: result.message, success: result.trade.amount_kwh > 0 };
    } catch (e) {
      return { message: e instanceof Error ? e.message : "Purchase failed.", success: false };
    }
  }

  async function handleSmartMatch(desiredKwh: number) {
    if (!buyerId) throw new Error("Select a household first.");
    const result = await api.smartMatch(buyerId, desiredKwh);
    await sim.refreshHouseholds();
    await loadMarketData();
    return result;
  }

  return (
    <div className="min-h-screen p-3 sm:p-6" style={{ background: "var(--page-bg)" }}>
      <div
        className="mx-auto flex w-full max-w-6xl flex-col gap-4 rounded-[32px] p-4 sm:p-6"
        style={{ background: "var(--panel-bg)" }}
      >
        <Header householdCount={sim.households.length} config={sim.config} />

        <Hero
          hour={sim.hour}
          marketState={sim.marketState}
          connection={sim.connection}
          isAdvancing={sim.isAdvancing}
          autoPlay={sim.autoPlay}
          error={sim.error}
          onAdvance={sim.advance}
          onToggleAutoPlay={sim.toggleAutoPlay}
        />

        <BuyerSelector households={sim.households} selectedId={buyerId} onSelect={setSelectedBuyerId} />

        <MarketPulse summary={summary} />

        {loadError && (
          <p
            className="inline-block self-start rounded-full px-3 py-1 text-sm font-medium"
            style={{ background: "var(--status-critical-soft)", color: "var(--status-critical)" }}
          >
            {loadError}
          </p>
        )}

        <PriceSparkline points={summary?.price_trend ?? []} />

        <SmartMatchCard buyerId={buyerId} onRun={handleSmartMatch} />

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <HighlightCard
            label="Best Price"
            listing={bestPriceListing}
            metric={bestPriceListing ? `Rs ${bestPriceListing.price_per_kwh.toFixed(2)}/kWh` : ""}
            icon={<TrendIcon className="h-5 w-5" />}
          />
          <HighlightCard
            label="Most Reliable"
            listing={mostReliableListing}
            metric={mostReliableListing ? `${Math.round(mostReliableListing.reliability_score * 100)}% reliable` : ""}
            icon={<ShieldIcon className="h-5 w-5" />}
          />
        </div>

        <ListingTable
          listings={shoppableListings}
          myZoneId={myZoneId}
          myNeedKwh={myNeedKwh}
          buyerId={buyerId}
          buyerName={me?.name ?? ""}
          onBuy={handleBuy}
        />
      </div>
    </div>
  );
}
