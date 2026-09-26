"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { PricePoint } from "@/components/PriceChart";
import { api } from "./api";
import type { Household, LedgerCheck, MarketState, SimConfig, Trade } from "./types";

const AUTO_PLAY_INTERVAL_MS = 1500;
// Live clock: how often to check whether a new hour has opened. The server does the
// actual advancing (it catches the simulation up on every request); this only asks.
const LIVE_POLL_MS = 20_000;
const HOUR_FLIP_GRACE_MS = 1500; // poll just after the expected hour boundary
// Free-tier hosting (Render) sleeps idle services; the first request can take ~a minute.
const SLOW_START_HINT_MS = 4000; // pending this long -> tell the user the server is waking up
const CONNECT_RETRY_MS = 3000;
const CONNECT_GIVE_UP_MS = 90_000;
const OFFLINE_MESSAGE = "Can't reach the WattShare API -- is the backend running?";

/** connecting: first load in flight. waking: it's slow or failing, still retrying. */
export type Connection = "connecting" | "waking" | "ready" | "offline";

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * The shared simulation clock every dashboard page reads from.
 *
 * Live clock (the default): the backend keeps the simulation on the real hour, so
 * this just polls and reloads when an hour turns over. Manual clock: advance() /
 * auto-play step through hours, as in the original prototype.
 */
export function useSimulation() {
  const [config, setConfig] = useState<SimConfig | null>(null);
  const [households, setHouseholds] = useState<Household[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [ledger, setLedger] = useState<LedgerCheck | null>(null);
  const [marketState, setMarketState] = useState<MarketState | null>(null);
  const [priceHistory, setPriceHistory] = useState<PricePoint[]>([]);
  const [hour, setHour] = useState(0);
  const [nextHourAt, setNextHourAt] = useState<number | null>(null); // epoch ms, live clock only
  const [isAdvancing, setIsAdvancing] = useState(false);
  const [autoPlay, setAutoPlay] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [connection, setConnection] = useState<Connection>("connecting");

  const advancingRef = useRef(false);
  const ticksRef = useRef<number | null>(null);

  /** Everything the dashboards show, fresh from the server. Asks for the clock first,
   *  which is also what makes a live server catch up to the current hour. */
  const loadAll = useCallback(async () => {
    const status = await api.getSimulationStatus();
    const nextHouseholds = await api.getHouseholds();
    const nextTrades = await api.getTrades();
    const nextMarketState = await api.getMarketState();
    const nextLedger = await api.verifyLedger();
    const summary = await api.getMarketSummary();
    setHouseholds(nextHouseholds);
    setTrades(nextTrades);
    setMarketState(nextMarketState);
    setLedger(nextLedger);
    setPriceHistory(summary.price_trend.map((p) => ({ hour: p.hour, price: p.clearing_price })));
    setHour(status.hour);
    setNextHourAt(status.seconds_to_next_hour != null ? Date.now() + status.seconds_to_next_hour * 1000 : null);
    ticksRef.current = status.total_ticks;
  }, []);

  useEffect(() => {
    let cancelled = false;
    const slowHint = setTimeout(() => {
      if (!cancelled) setConnection((c) => (c === "connecting" ? "waking" : c));
    }, SLOW_START_HINT_MS);

    (async () => {
      const deadline = Date.now() + CONNECT_GIVE_UP_MS;
      while (!cancelled) {
        try {
          const initialConfig = await api.getConfig();
          await loadAll();
          if (cancelled) return;
          setConfig(initialConfig);
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
  }, [loadAll]);

  const live = config?.clock === "live";

  // Live clock: poll, and reload everything when the hour has turned over.
  useEffect(() => {
    if (!live || connection !== "ready") return;
    let cancelled = false;

    async function poll() {
      try {
        const status = await api.getSimulationStatus();
        if (cancelled) return;
        setNextHourAt(status.seconds_to_next_hour != null ? Date.now() + status.seconds_to_next_hour * 1000 : null);
        if (status.total_ticks !== ticksRef.current) await loadAll();
        if (!cancelled) setError(null);
      } catch {
        if (!cancelled) setError(OFFLINE_MESSAGE);
      }
    }

    const interval = setInterval(poll, LIVE_POLL_MS);
    const onVisible = () => {
      if (document.visibilityState === "visible") poll();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      cancelled = true;
      clearInterval(interval);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [live, connection, loadAll]);

  // ...and poll right as the next hour is due, so the flip isn't up to 20 s late.
  useEffect(() => {
    if (!live || nextHourAt == null) return;
    const timer = setTimeout(
      async () => {
        try {
          const status = await api.getSimulationStatus();
          if (status.total_ticks !== ticksRef.current) await loadAll();
          else setNextHourAt(status.seconds_to_next_hour != null ? Date.now() + status.seconds_to_next_hour * 1000 : null);
        } catch {
          setError(OFFLINE_MESSAGE);
        }
      },
      Math.max(nextHourAt - Date.now(), 0) + HOUR_FLIP_GRACE_MS,
    );
    return () => clearTimeout(timer);
  }, [live, nextHourAt, loadAll]);

  async function advance() {
    if (live || advancingRef.current) return;
    advancingRef.current = true;
    setIsAdvancing(true);
    try {
      // Close the current hour, then open the next. The marketplace trades during
      // an hour; the dispatcher clears whatever surplus/deficit is left when it
      // closes -- dispatching first thing would leave the marketplace nothing to sell.
      await api.match();
      await api.tick();
      await loadAll();
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
    if (!autoPlay || live) return;
    const id = setInterval(advance, AUTO_PLAY_INTERVAL_MS);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoPlay, live]);

  /** Re-read households after a marketplace trade changed their open positions. */
  async function refreshHouseholds() {
    try {
      setHouseholds(await api.getHouseholds());
    } catch {
      // The next poll/advance will surface connectivity problems; a stale table is harmless.
    }
  }

  return {
    connection,
    live,
    nextHourAt,
    refreshHouseholds,
    ledger,
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
