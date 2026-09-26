"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useSimulation } from "@/lib/useSimulation";
import type { Listing, PricingMode, SellerStats } from "@/lib/types";
import { Header } from "@/components/Header";
import { Hero } from "@/components/Hero";
import { SellerSelector } from "@/components/SellerSelector";
import { SurplusCard } from "@/components/SurplusCard";
import { ReliabilityCard } from "@/components/ReliabilityCard";
import { StatTile } from "@/components/StatTile";
import { ImpactCard } from "@/components/ImpactCard";
import { BatteryCard } from "@/components/BatteryCard";

const BASE_PRICE_FALLBACK = 6.0; // mirrors backend/market/pricing.py's BASE_PRICE, used only to
// prefill the manual-price field before any market cycle has run yet

export default function SellerPage() {
  const sim = useSimulation();
  const solarHouseholds = sim.households.filter((h) => h.has_solar);

  const [selectedSellerId, setSelectedSellerId] = useState<string | null>(null);
  // Falls back to the first solar household once the list loads, without needing
  // an effect just to mirror that default into state.
  const sellerId = selectedSellerId ?? solarHouseholds[0]?.id ?? null;

  const [listing, setListing] = useState<Listing | null>(null);
  const [stats, setStats] = useState<SellerStats | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  function selectSeller(id: string) {
    setSelectedSellerId(id);
    setListing(null);
    setStats(null);
  }

  async function saveListing(mode: PricingMode, price: number | null) {
    if (!sellerId) return;
    setSaving(true);
    setSaveError(null);
    try {
      const updated = await api.saveListing(sellerId, mode, price);
      setListing(updated);
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Couldn't save listing");
    } finally {
      setSaving(false);
    }
  }

  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (!sellerId) return;
    let cancelled = false;
    (async () => {
      try {
        // Sequential, not Promise.all: a request that fails shouldn't take an
        // already-succeeded one down with it.
        const fetchedListing = await api.getSellerListing(sellerId);
        if (cancelled) return;
        if (fetchedListing) {
          setListing(fetchedListing);
        } else {
          // New sellers start opted in to auto-sell, so their surplus is live by default.
          await saveListing("auto", null);
        }

        const fetchedStats = await api.getSellerStats(sellerId);
        if (cancelled) return;
        setStats(fetchedStats);
        setLoadError(null);
      } catch (e) {
        if (!cancelled) setLoadError(e instanceof Error ? e.message : "Couldn't load seller data");
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sellerId, sim.hour]);

  const me = sim.households.find((h) => h.id === sellerId) ?? null;
  // What's still unsold this hour, after the home's battery has taken its share.
  const currentSurplusKwh = me ? Math.max(me.open_net_kwh, 0) : 0;
  const defaultPrice = sim.marketState?.clearing_price ?? BASE_PRICE_FALLBACK;

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

        <SellerSelector households={solarHouseholds} selectedId={sellerId} onSelect={selectSeller} />

        {loadError && (
          <p
            className="inline-block self-start rounded-full px-3 py-1 text-sm font-medium"
            style={{ background: "var(--status-critical-soft)", color: "var(--status-critical)" }}
          >
            {loadError}
          </p>
        )}

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <SurplusCard
              key={listing?.id ?? "pending"}
              householdName={me?.name ?? ""}
              currentSurplusKwh={currentSurplusKwh}
              listing={listing}
              defaultPrice={defaultPrice}
              onSave={saveListing}
              saving={saving}
              error={saveError}
            />
          </div>
          <ReliabilityCard score={stats?.reliability_score ?? null} />
        </div>

        {me && me.battery_capacity_kwh > 0 && <BatteryCard household={me} />}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <StatTile label="Earnings today" value={`Rs ${(stats?.earnings_today ?? 0).toFixed(2)}`} />
          <StatTile label="This week" value={`Rs ${(stats?.earnings_week ?? 0).toFixed(2)}`} />
          <StatTile label="Lifetime" value={`Rs ${(stats?.earnings_lifetime ?? 0).toFixed(2)}`} />
        </div>

        <ImpactCard totalKwhSold={stats?.total_kwh_sold_lifetime ?? 0} />
      </div>
    </div>
  );
}
