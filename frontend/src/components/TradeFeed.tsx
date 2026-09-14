import type { Trade } from "@/lib/types";
import { Card } from "./Card";

export function TradeFeed({ trades }: { trades: Trade[] }) {
  const recent = [...trades].reverse();

  return (
    <Card title="Trade Feed" subtitle={`${trades.length} trade(s) so far`}>
      <div className="max-h-72 overflow-y-auto">
        {recent.length === 0 ? (
          <p className="py-6 text-center text-sm" style={{ color: "var(--foreground-muted)" }}>
            No trades yet -- advance the simulation to start matching.
          </p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr style={{ color: "var(--foreground-muted)" }}>
                <th className="pb-2 font-medium">Hour</th>
                <th className="pb-2 font-medium">Seller</th>
                <th className="pb-2 font-medium">Buyer</th>
                <th className="pb-2 pr-2 text-right font-medium">Amount</th>
                <th className="pb-2 text-right font-medium">Price</th>
              </tr>
            </thead>
            <tbody className="tabular-nums" style={{ color: "var(--foreground)" }}>
              {recent.map((t) => (
                <tr key={t.id} className="border-t" style={{ borderColor: "var(--grid-line)" }}>
                  <td className="py-1.5">{String(t.timestamp).padStart(2, "0")}:00</td>
                  <td className="py-1.5">{t.seller_id}</td>
                  <td className="py-1.5">{t.buyer_id}</td>
                  <td className="py-1.5 pr-2 text-right">{t.amount_kwh.toFixed(2)} kWh</td>
                  <td className="py-1.5 text-right">Rs {t.price_per_kwh.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </Card>
  );
}
