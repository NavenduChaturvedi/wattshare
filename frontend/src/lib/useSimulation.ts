"use client";

import { useEffect, useRef, useState } from "react";
import type { PricePoint } from "@/components/PriceChart";
import { api } from "./api";
import type { Household, MarketState, SimConfig, Trade } from "./types";

const AUTO_PLAY_INTERVAL_MS = 1500;

/** Drives the shared simulation clock (advance/auto-play) that every dashboard page reads from. */
export function useSimulation() {
  const [config, setConfig] = useState<SimConfig | null>(null);
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
        const initialConfig = await api.getConfig();
        setConfig(initialConfig);
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

      // Re-read households: the match just booked trades against their positions.
      const matchedHouseholds = await api.getHouseholds();
      setHouseholds(matchedHouseholds);

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

  return {
    config,
    households,
    trades,
    marketState,
    priceHistory,
    hour,
    isAdvancing,
    autoPlay,
    error,
    advance,
    toggleAutoPlay: () => setAutoPlay((v) => !v),
  };
}
