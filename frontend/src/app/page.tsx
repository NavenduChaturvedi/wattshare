"use client";

import { Header } from "@/components/Header";
import { Hero } from "@/components/Hero";
import { HouseholdTable } from "@/components/HouseholdTable";
import { GenerationChart } from "@/components/GenerationChart";
import { PriceChart } from "@/components/PriceChart";
import { TradeFeed } from "@/components/TradeFeed";
import { useSimulation } from "@/lib/useSimulation";

export default function Home() {
  const sim = useSimulation();

  return (
    <div className="min-h-screen p-3 sm:p-6" style={{ background: "var(--page-bg)" }}>
      <div
        className="mx-auto flex w-full max-w-6xl flex-col gap-4 rounded-[32px] p-4 sm:p-6"
        style={{ background: "var(--panel-bg)" }}
      >
        <Header householdCount={sim.households.length} />

        <Hero
          hour={sim.hour}
          marketState={sim.marketState}
          isAdvancing={sim.isAdvancing}
          autoPlay={sim.autoPlay}
          error={sim.error}
          onAdvance={sim.advance}
          onToggleAutoPlay={sim.toggleAutoPlay}
        />

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <PriceChart data={sim.priceHistory} />
          <GenerationChart households={sim.households} />
        </div>

        <HouseholdTable households={sim.households} />
        <TradeFeed trades={sim.trades} />
      </div>
    </div>
  );
}
