"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { BuyerListing, PurchaseQuote } from "@/lib/types";

export interface PurchaseResult {
  message: string;
  success: boolean;
}

const QUOTE_DEBOUNCE_MS = 250;
const QUICK_PICKS = [
  { label: "25%", share: 0.25 },
  { label: "50%", share: 0.5 },
  { label: "Max", share: 1 },
];

/**
 * Choose-your-amount purchase. Every amount is priced by the server's quote
 * endpoint -- the same caps the purchase applies (your remaining need, what the
 * seller can actually deliver) -- and the confirmed price is sent back as a guard,
 * so the trade can't come out different from what was shown.
 */
export function BuyDialog({
  listing,
  buyerId,
  buyerName,
  onConfirm,
  onClose,
}: {
  listing: BuyerListing;
  buyerId: string;
  buyerName: string;
  onConfirm: (amountKwh: number, maxPricePerKwh: number) => Promise<PurchaseResult>;
  onClose: (result?: PurchaseResult) => void;
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [quote, setQuote] = useState<PurchaseQuote | null>(null);
  const [amountText, setAmountText] = useState("");
  const [quoting, setQuoting] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    dialogRef.current?.showModal();
  }, []);

  // First quote: the most this buyer can take from this listing.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const q = await api.getQuote(listing.id, buyerId);
        if (cancelled) return;
        setQuote(q);
        setAmountText(q.max_kwh.toFixed(2));
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Couldn't price this listing");
      } finally {
        if (!cancelled) setQuoting(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [listing.id, buyerId, refreshKey]);

  const amount = Number(amountText);
  const amountValid = amountText.trim() !== "" && Number.isFinite(amount) && amount > 0;

  // Re-quote whenever the amount changes.
  useEffect(() => {
    if (!amountValid || !quote) return;
    if (Math.abs(quote.requested_kwh - amount) < 0.0005) return;
    let cancelled = false;
    const timer = setTimeout(async () => {
      setQuoting(true);
      try {
        const q = await api.getQuote(listing.id, buyerId, amount);
        if (!cancelled) {
          setQuote(q);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Couldn't price that amount");
      } finally {
        if (!cancelled) setQuoting(false);
      }
    }, QUOTE_DEBOUNCE_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [amount, amountValid, quote, listing.id, buyerId]);

  const maxKwh = quote?.max_kwh ?? 0;
  const quoteMatchesInput = !!quote && amountValid && Math.abs(quote.requested_kwh - amount) < 0.0005;
  const capped = quoteMatchesInput && quote!.amount_kwh < quote!.requested_kwh - 0.0005;
  const canConfirm = quoteMatchesInput && quote!.amount_kwh > 0 && !quoting && !submitting;

  async function confirm() {
    if (!quote || !canConfirm) return;
    setSubmitting(true);
    setError(null);
    const result = await onConfirm(quote.amount_kwh, quote.price_per_kwh);
    setSubmitting(false);
    if (result.success) {
      onClose(result);
    } else {
      // e.g. the price moved (409) or the need changed: show why and re-price from scratch.
      setError(result.message);
      setQuoting(true);
      setRefreshKey((k) => k + 1);
    }
  }

  const nothingToBuy = quote && quote.max_kwh <= 0;

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby="buy-dialog-title"
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      onClick={(e) => {
        if (e.target === dialogRef.current) onClose(); // click on the backdrop
      }}
      className="m-auto w-[calc(100%-2rem)] max-w-md rounded-3xl p-0 backdrop:bg-black/40"
      style={{ background: "var(--card-bg)", color: "var(--ink)" }}
    >
      <div className="flex flex-col gap-4 p-5 sm:p-6">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 id="buy-dialog-title" className="text-lg font-semibold">
              Buy from {listing.seller_name}
            </h2>
            <p className="text-xs" style={{ color: "var(--ink-muted)" }}>
              as {buyerName} &middot; Rs {(quote?.price_per_kwh ?? listing.price_per_kwh).toFixed(2)}/kWh
            </p>
          </div>
          <button
            onClick={() => onClose()}
            aria-label="Close"
            className="rounded-full px-2 py-1 text-sm"
            style={{ color: "var(--ink-muted)" }}
          >
            &#x2715;
          </button>
        </div>

        {quote && (
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <div className="rounded-2xl p-3" style={{ background: "var(--panel-bg)" }}>
              <dt className="text-xs" style={{ color: "var(--ink-muted)" }}>
                You need this hour
              </dt>
              <dd className="font-semibold tabular-nums">{quote.buyer_need_kwh.toFixed(2)} kWh</dd>
            </div>
            <div className="rounded-2xl p-3" style={{ background: "var(--panel-bg)" }}>
              <dt className="text-xs" style={{ color: "var(--ink-muted)" }}>
                Seller can deliver
              </dt>
              <dd className="font-semibold tabular-nums">{quote.deliverable_kwh.toFixed(2)} kWh</dd>
            </div>
          </dl>
        )}

        {quote?.stale && (
          <p
            className="rounded-2xl px-3 py-2 text-xs"
            style={{ background: "var(--accent-soft)", color: "var(--accent)" }}
          >
            This listing advertises {quote.advertised_kwh.toFixed(2)} kWh, but the seller can only deliver{" "}
            {quote.deliverable_kwh.toFixed(2)} kWh right now.
          </p>
        )}

        {nothingToBuy ? (
          <p className="text-sm" style={{ color: "var(--ink-secondary)" }}>
            {quote!.buyer_need_kwh <= 0
              ? "Your deficit is already covered this hour -- nothing to buy."
              : "This seller has nothing deliverable right now."}
          </p>
        ) : (
          <div className="flex flex-col gap-3">
            <label className="flex items-center gap-2 text-sm">
              <span style={{ color: "var(--ink-secondary)" }}>Amount</span>
              <input
                type="number"
                inputMode="decimal"
                min={0.01}
                max={maxKwh || undefined}
                step={0.01}
                value={amountText}
                onChange={(e) => setAmountText(e.target.value)}
                disabled={!quote}
                className="w-28 rounded-full border px-3 py-1.5 text-sm tabular-nums"
                style={{ borderColor: "var(--border)", background: "var(--panel-bg)", color: "var(--ink)" }}
                aria-describedby="buy-dialog-preview"
              />
              <span style={{ color: "var(--ink-muted)" }}>kWh</span>
            </label>

            <input
              type="range"
              min={0}
              max={maxKwh}
              step={0.01}
              value={amountValid ? Math.min(amount, maxKwh) : 0}
              onChange={(e) => setAmountText(Number(e.target.value).toFixed(2))}
              disabled={!quote || maxKwh <= 0}
              aria-label="Amount to buy"
              className="w-full"
              style={{ accentColor: "var(--accent)" }}
            />

            <div className="flex gap-2">
              {QUICK_PICKS.map((p) => (
                <button
                  key={p.label}
                  onClick={() => setAmountText((maxKwh * p.share).toFixed(2))}
                  disabled={!quote || maxKwh <= 0}
                  className="rounded-full px-3 py-1 text-xs font-medium disabled:opacity-50"
                  style={{ background: "var(--panel-bg)", color: "var(--ink)" }}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>
        )}

        <div id="buy-dialog-preview" className="rounded-2xl p-4" style={{ background: "var(--panel-bg)" }} aria-live="polite">
          {!quote ? (
            <p className="text-sm" style={{ color: "var(--ink-muted)" }}>
              {quoting ? "Getting a price..." : "No price available."}
            </p>
          ) : !amountValid ? (
            <p className="text-sm" style={{ color: "var(--ink-muted)" }}>
              Enter an amount above 0.
            </p>
          ) : (
            <>
              <p className="text-sm tabular-nums" style={{ color: "var(--ink-secondary)" }}>
                {quote.amount_kwh.toFixed(2)} kWh &times; Rs {quote.price_per_kwh.toFixed(2)}
                {quoting && <span style={{ color: "var(--ink-muted)" }}> &middot; updating...</span>}
              </p>
              <p className="text-2xl font-bold tabular-nums">Rs {quote.total_cost.toFixed(2)}</p>
              {capped && (
                <p className="mt-1 text-xs" style={{ color: "var(--accent)" }}>
                  Capped at {quote.max_kwh.toFixed(2)} kWh -- the most you can buy here right now.
                </p>
              )}
            </>
          )}
        </div>

        {error && (
          <p className="text-sm" role="alert" style={{ color: "var(--status-critical)" }}>
            {error}
          </p>
        )}

        <div className="flex justify-end gap-2">
          <button
            onClick={() => onClose()}
            className="rounded-full px-4 py-2 text-sm font-medium"
            style={{ background: "var(--panel-bg)", color: "var(--ink)" }}
          >
            Cancel
          </button>
          <button
            onClick={confirm}
            disabled={!canConfirm}
            className="rounded-full px-4 py-2 text-sm font-medium disabled:opacity-50"
            style={{ background: "var(--accent)", color: "var(--accent-contrast)" }}
          >
            {submitting
              ? "Buying..."
              : quoteMatchesInput && quote!.amount_kwh > 0
                ? `Buy ${quote!.amount_kwh.toFixed(2)} kWh for Rs ${quote!.total_cost.toFixed(2)}`
                : "Buy"}
          </button>
        </div>
      </div>
    </dialog>
  );
}
