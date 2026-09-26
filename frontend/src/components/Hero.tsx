"use client";

import { useEffect, useState } from "react";
import type { MarketState } from "@/lib/types";
import type { Connection } from "@/lib/useSimulation";
import { ArrowRightIcon, PauseIcon, PlayIcon } from "./icons";

function formatCountdown(ms: number): string {
  if (ms <= 0) return "any moment";
  const minutes = Math.ceil(ms / 60_000);
  if (ms < 60_000) return `in ${Math.ceil(ms / 1000)} s`;
  return minutes === 1 ? "in 1 min" : `in ${minutes} min`;
}

/** Short zone label for the clock, e.g. "IST" for Asia/Kolkata. */
function zoneLabel(timezone: string | null): string {
  if (!timezone) return "";
  try {
    const part = new Intl.DateTimeFormat("en-IN", { timeZone: timezone, timeZoneName: "short" })
      .formatToParts(new Date())
      .find((p) => p.type === "timeZoneName");
    return part?.value ?? timezone;
  } catch {
    return timezone;
  }
}

function LiveBadge({
  nextHourAt,
  timezone,
  speed,
}: {
  nextHourAt: number | null;
  timezone: string | null;
  speed: number;
}) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="flex flex-col gap-1.5" role="status" aria-live="off">
      <span
        className="inline-flex items-center gap-2 self-start rounded-full px-3 py-1.5 text-xs font-semibold uppercase tracking-wide"
        style={{ background: "var(--status-good-soft)", color: "var(--status-good)" }}
      >
        <span className="relative flex h-2 w-2" aria-hidden>
          <span
            className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-60"
            style={{ background: "var(--status-good)" }}
          />
          <span className="relative inline-flex h-2 w-2 rounded-full" style={{ background: "var(--status-good)" }} />
        </span>
        Live{zoneLabel(timezone) && ` · ${zoneLabel(timezone)}`}
        {speed !== 1 && ` · ${speed}×`}
      </span>
      <span className="text-xs tabular-nums" style={{ color: "var(--ink-muted)" }}>
        {nextHourAt != null ? `Next hour ${formatCountdown(nextHourAt - now)}` : "Following the clock"}
      </span>
    </div>
  );
}

export function Hero({
  hour,
  marketState,
  connection,
  live,
  nextHourAt,
  timezone,
  clockSpeed,
  isAdvancing,
  autoPlay,
  error,
  onAdvance,
  onToggleAutoPlay,
}: {
  hour: number;
  marketState: MarketState | null;
  connection: Connection;
  live: boolean;
  nextHourAt: number | null;
  timezone: string | null;
  clockSpeed: number;
  isAdvancing: boolean;
  autoPlay: boolean;
  error: string | null;
  onAdvance: () => void;
  onToggleAutoPlay: () => void;
}) {
  const price = marketState?.clearing_price ?? null;
  const ready = connection === "ready";

  return (
    <section
      className="flex flex-col gap-6 rounded-3xl p-6 sm:flex-row sm:items-center sm:gap-8"
      style={{ background: "var(--card-bg)" }}
    >
      <div className="flex items-center gap-4">
        <div
          className="flex h-20 w-20 shrink-0 flex-col items-center justify-center rounded-full"
          style={{ background: "var(--panel-bg)", color: "var(--ink)" }}
        >
          <span className="text-2xl font-bold leading-none tabular-nums">{String(hour).padStart(2, "0")}</span>
          <span className="mt-1 text-[10px] uppercase tracking-wide" style={{ color: "var(--ink-muted)" }}>
            Hour
          </span>
        </div>

        <div className="h-12 w-px" style={{ background: "var(--border)" }} />

        {live ? (
          <LiveBadge nextHourAt={nextHourAt} timezone={timezone} speed={clockSpeed} />
        ) : (
          <div className="flex flex-col gap-2">
            <button
              onClick={onAdvance}
              disabled={!ready || isAdvancing || autoPlay}
              className="inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-opacity disabled:opacity-50"
              style={{ background: "var(--accent)", color: "var(--accent-contrast)" }}
            >
              {isAdvancing ? "Advancing..." : "Advance Hour"}
              <ArrowRightIcon className="h-4 w-4" />
            </button>
            <button
              onClick={onToggleAutoPlay}
              disabled={!ready}
              className="inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-opacity disabled:opacity-50"
              style={
                autoPlay
                  ? { background: "var(--strong)", color: "var(--strong-contrast)" }
                  : { background: "var(--panel-bg)", color: "var(--ink)" }
              }
            >
              {autoPlay ? <PauseIcon className="h-3.5 w-3.5" /> : <PlayIcon className="h-3.5 w-3.5" />}
              {autoPlay ? "Stop" : "Auto-play"}
            </button>
          </div>
        )}
      </div>

      <div className="flex-1">
        {error ? (
          <p
            className="inline-block rounded-full px-3 py-1 text-sm font-medium"
            style={{ background: "var(--status-critical-soft)", color: "var(--status-critical)" }}
          >
            {error}
          </p>
        ) : !ready ? (
          <div role="status" aria-live="polite">
            <h2 className="flex items-center gap-3 text-2xl font-bold sm:text-3xl" style={{ color: "var(--ink)" }}>
              <span
                className="h-3 w-3 shrink-0 animate-pulse rounded-full"
                style={{ background: "var(--accent)" }}
                aria-hidden
              />
              {connection === "waking" ? "Waking up the server..." : "Connecting..."}
            </h2>
            <p className="mt-1 text-sm" style={{ color: "var(--ink-secondary)" }}>
              {connection === "waking"
                ? "The demo backend sleeps when idle on free hosting -- the first load can take up to a minute."
                : "Loading the neighborhood."}
            </p>
          </div>
        ) : price !== null ? (
          <>
            <h2 className="text-3xl font-bold tabular-nums sm:text-4xl" style={{ color: "var(--ink)" }}>
              Rs {price.toFixed(2)}
              <span className="text-lg font-medium" style={{ color: "var(--ink-muted)" }}>
                {" "}
                /kWh
              </span>
            </h2>
            <p className="mt-1 text-sm" style={{ color: "var(--ink-secondary)" }}>
              {String(marketState!.timestamp ?? 0).padStart(2, "0")}:00 cleared at this price &middot; supply{" "}
              {marketState!.total_supply_kwh.toFixed(1)} kWh &middot; demand{" "}
              {marketState!.total_demand_kwh.toFixed(1)} kWh
              {marketState!.transformer_load_pct != null && (
                <>
                  {" "}
                  &middot; transformer {marketState!.transformer_load_kw >= 0 ? "importing" : "exporting"}{" "}
                  {Math.round(marketState!.transformer_load_pct)}%
                </>
              )}
            </p>
          </>
        ) : marketState?.timestamp != null ? (
          // An hour closed with no local supply (night, before batteries kick in): no price to show.
          <>
            <h2 className="text-3xl font-bold sm:text-4xl" style={{ color: "var(--ink)" }}>
              Grid only
            </h2>
            <p className="mt-1 text-sm" style={{ color: "var(--ink-secondary)" }}>
              {String(marketState.timestamp).padStart(2, "0")}:00 had no local supply &middot; demand{" "}
              {marketState.total_demand_kwh.toFixed(1)} kWh came from the grid
              {marketState.transformer_load_pct != null &&
                ` · transformer importing ${Math.round(marketState.transformer_load_pct)}%`}
            </p>
          </>
        ) : (
          <>
            <h2 className="text-3xl font-bold sm:text-4xl" style={{ color: "var(--ink)" }}>
              Ready to trade &#9889;
            </h2>
            <p className="mt-1 text-sm" style={{ color: "var(--ink-secondary)" }}>
              {live
                ? "The marketplace is open. When the hour turns, the dispatcher clears what's left."
                : "The marketplace is open. Advance the hour to let the dispatcher clear what's left."}
            </p>
          </>
        )}
      </div>
    </section>
  );
}
