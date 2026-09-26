"use client";

import { useEffect, useRef, useState } from "react";
import type { PricePoint } from "@/components/PriceChart";
import { api } from "./api";
import type { Household, MarketState, SimConfig, Trade } from "./types";

const AUTO_PLAY_INTERVAL_MS = 1500;
// Free-tier hosting (Render) sleeps idle services; the first request can take ~a minute.
const SLOW_START_HINT_MS = 4000; // pending this long -> tell the user the server is waking up
const CONNECT_RETRY_MS = 3000;
const CONNECT_GIVE_UP_MS = 90_000;
const OFFLINE_MESSAGE = "Can't reach the WattShare API -- is the backend running?";

/** connecting: first load in flight. waking: it's slow or failing, still retrying. */
export type Connection = "connecting" | "waking" | "ready" | "offline";

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

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
  const [connection, setConnection] = useState<Connection>("connecting");

  const advancingRef = useRef(false);

  useEffect(() => {
    let cancelled = false;
    const slowHint = setTimeout(() => {
      if (!cancelled) setConnection((c) => (c === "connecting" ? "waking" : c));
    }, SLOW_START_HINT_MS);

    (async () => {
      const deadline = Date.now() + CONNECT_GIVE_UP_MS;
      while (!cancelled) {
        try {
          const initialHouseholds = await api.getHouseholds();
          const initialTrades = await api.getTrades();
          const initialMarketState = await api.getMarketState();
          const initialConfig = await api.getConfig();
        const status = await api.getSimulationStatus();
          if (cancelled) return;
          setConfig(initialConfig);
          setHouseholds(initialHouseholds);
          setTrades(initialTrades);
          setMarketState(initialMarketState);
          setHour(status.hour);
          if (initialMarketState.timestamp !== null && initialMarketState.clearing_price !== null) {
            setPriceHistory([{ hour: initialMarketState.timestamp, price: initialMarketState.clearing_price }]);
          }
          setConnection("ready");
          return;
        } catch {
          if (cancelled) return;
          if (Date.now() >= deadline) {
            setConnection("offline");
            setError(OFFLINE_MESSAGE);
            return;
          }
          setConnection("waking");
          await sleep(CONNECT_RETRY_MS);
        }
      }
    })();

    return () => {
      cancelled = true;
      clearTimeout(slowHint);
    };
  }, []);

  async function advance() {
    if (advancingRef.current) return;
    advancingRef.current = true;
    setIsAdvancing(true);
    try {
      // Close the current hour, then open the next. The marketplace trades during
      // an hour; the dispatcher clears whatever surplus/deficit is left when it
      // closes -- dispatching first thing would leave the marketplace nothing to sell.
      const matchResult = await api.match();
      const closed = matchResult.market_state;
      setMarketState(closed);
      if (closed.timestamp !== null && closed.clearing_price !== null) {
        setPriceHistory((prev) => [...prev, { hour: closed.timestamp!, price: closed.clearing_price! }]);
      }

      const tickResult = await api.tick();
      setHouseholds(tickResult.households);
      setHour(tickResult.hour);

      const tradeHistory = await api.getTrades();
      setTrades(tradeHistory);
      setError(null);
    } catch {
      setError(OFFLINE_MESSAGE);
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
    connection,
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
