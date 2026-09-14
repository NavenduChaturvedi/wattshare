"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { Household, MarketState, Trade } from "@/lib/types";
import { Header } from "@/components/Header";
import { Hero } from "@/components/Hero";
import { HouseholdTable } from "@/components/HouseholdTable";
import { GenerationChart } from "@/components/GenerationChart";
import { PriceChart, type PricePoint } from "@/components/PriceChart";
import { TradeFeed } from "@/components/TradeFeed";

const AUTO_PLAY_INTERVAL_MS = 1500;

export default function Home() {
  const [households, setHouseholds] = useState<Household[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [marketState, setMarketState] = useState<MarketState | null>(null);
  const [priceHistory, setPriceHistory] = useState<PricePoint[]>([]);
  const [hour, setHour] = useState(0);
  const [isAdvancing, setIsAdvancing] = useState(false);
  const [autoPlay, setAutoPlay] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const advancingRef = useRef(false);

  useEffect(() => {
    (async () => {
      try {
        const initialHouseholds = await api.getHouseholds();
        const initialTrades = await api.getTrades();
        const initialMarketState = await api.getMarketState();
        setHouseholds(initialHouseholds);
        setTrades(initialTrades);
        setMarketState(initialMarketState);
        setHour(initialMarketState.timestamp ?? 0);
        if (initialMarketState.timestamp !== null && initialMarketState.clearing_price !== null) {
          setPriceHistory([{ hour: initialMarketState.timestamp, price: initialMarketState.clearing_price }]);
        }
      } catch {
        setError("Can't reach the WattShare API -- is the backend running?");
      }
    })();
  }, []);

  async function advance() {
    if (advancingRef.current) return;
    advancingRef.current = true;
    setIsAdvancing(true);
    try {
      const tickResult = await api.tick();
      setHouseholds(tickResult.households);
      setHour(tickResult.hour);

      const matchResult = await api.match();
      setMarketState(matchResult.market_state);
      if (matchResult.market_state.clearing_price !== null) {
        setPriceHistory((prev) => [...prev, { hour: tickResult.hour, price: matchResult.market_state.clearing_price! }]);
      }

      const tradeHistory = await api.getTrades();
      setTrades(tradeHistory);
      setError(null);
    } catch {
      setError("Can't reach the WattShare API -- is the backend running?");
      setAutoPlay(false);
    } finally {
      setIsAdvancing(false);
      advancingRef.current = false;
    }
  }

  useEffect(() => {
    if (!autoPlay) return;
    const id = setInterval(advance, AUTO_PLAY_INTERVAL_MS);
    return () => clearInterval(id);
  }, [autoPlay]);

  return (
    <div className="min-h-screen p-3 sm:p-6" style={{ background: "var(--page-bg)" }}>
      <div
        className="mx-auto flex w-full max-w-6xl flex-col gap-4 rounded-[32px] p-4 sm:p-6"
        style={{ background: "var(--panel-bg)" }}
      >
        <Header householdCount={households.length} />

        <Hero
          hour={hour}
          marketState={marketState}
          isAdvancing={isAdvancing}
          autoPlay={autoPlay}
          error={error}
          onAdvance={advance}
          onToggleAutoPlay={() => setAutoPlay((v) => !v)}
        />

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <PriceChart data={priceHistory} />
          <GenerationChart households={households} />
        </div>

        <HouseholdTable households={households} />
        <TradeFeed trades={trades} />
      </div>
    </div>
  );
}
