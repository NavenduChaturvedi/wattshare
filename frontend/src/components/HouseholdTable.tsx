import type { Household } from "@/lib/types";
import { Card } from "./Card";

function StatusBadge({ net }: { net: number }) {
  if (Math.abs(net) < 0.01) {
    return (
      <span className="text-xs" style={{ color: "var(--foreground-muted)" }}>
        Balanced
      </span>
    );
  }
  const selling = net > 0;
  return (
    <span
      className="inline-flex items-center gap-1 text-xs font-medium"
      style={{ color: selling ? "var(--status-good)" : "var(--status-critical)" }}
    >
      <span aria-hidden>{selling ? "▲" : "▼"}</span>
      {selling ? "Selling" : "Buying"}
    </span>
  );
}

export function HouseholdTable({ households }: { households: Household[] }) {
  return (
    <Card title="Households" subtitle={`${households.length} homes in the neighborhood`}>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr style={{ color: "var(--foreground-muted)" }}>
              <th className="pb-2 font-medium">ID</th>
              <th className="pb-2 font-medium">Name</th>
              <th className="pb-2 font-medium">Solar</th>
              <th className="pb-2 pr-2 text-right font-medium">Gen (kWh)</th>
              <th className="pb-2 pr-2 text-right font-medium">Cons (kWh)</th>
              <th className="pb-2 pr-2 text-right font-medium">Net (kWh)</th>
              <th className="pb-2 text-right font-medium">Status</th>
            </tr>
          </thead>
          <tbody className="tabular-nums" style={{ color: "var(--foreground)" }}>
            {households.map((h) => {
              const net = h.current_generation_kwh - h.current_consumption_kwh;
              return (
                <tr key={h.id} className="border-t" style={{ borderColor: "var(--grid-line)" }}>
                  <td className="py-1.5">{h.id}</td>
                  <td className="py-1.5">{h.name}</td>
                  <td className="py-1.5">{h.has_solar ? "Yes" : "No"}</td>
                  <td className="py-1.5 pr-2 text-right">{h.current_generation_kwh.toFixed(2)}</td>
                  <td className="py-1.5 pr-2 text-right">{h.current_consumption_kwh.toFixed(2)}</td>
                  <td className="py-1.5 pr-2 text-right">{net.toFixed(2)}</td>
                  <td className="py-1.5 text-right">
                    <StatusBadge net={net} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
