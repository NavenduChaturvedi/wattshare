import type { Trade } from "@/lib/types";
import { Card } from "./Card";
import { ListIcon } from "./icons";

export function TradeFeed({ trades }: { trades: Trade[] }) {
  const recent = [...trades].reverse();

  return (
    <Card title="Trade Feed" subtitle={`${trades.length} trade(s) so far`} icon={<ListIcon className="h-4 w-4" />}>
      <div className="max-h-72 overflow-y-auto">
        {recent.length === 0 ? (
          <p className="py-6 text-center text-sm" style={{ color: "var(--ink-muted)" }}>
            No trades yet -- advance the simulation to start matching.
          </p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr style={{ color: "var(--ink-muted)" }}>
                <th className="pb-2 font-medium">Hour</th>
                <th className="pb-2 font-medium">Seller</th>
                <th className="pb-2 font-medium">Buyer</th>
                <th className="pb-2 pr-2 text-right font-medium">Amount</th>
                <th className="pb-2 text-right font-medium">Price</th>
              </tr>
            </thead>
            <tbody className="tabular-nums" style={{ color: "var(--ink)" }}>
              {recent.map((t) => (
                <tr key={t.id} className="border-t" style={{ borderColor: "var(--grid-line)" }}>
                  <td className="py-2">
                    <span
                      className="inline-flex rounded-full px-2 py-0.5 text-xs font-medium"
                      style={{ background: "var(--panel-bg)", color: "var(--ink-secondary)" }}
                    >
                      {String(t.timestamp).padStart(2, "0")}:00
                    </span>
                  </td>
                  <td className="py-2">{t.seller_id}</td>
                  <td className="py-2">{t.buyer_id}</td>
                  <td className="py-2 pr-2 text-right">{t.amount_kwh.toFixed(2)} kWh</td>
                  <td className="py-2 text-right font-medium">Rs {t.price_per_kwh.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </Card>
  );
}
