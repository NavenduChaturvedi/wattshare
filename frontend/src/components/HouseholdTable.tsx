import type { Household } from "@/lib/types";
import { Card } from "./Card";
import { HomeIcon } from "./icons";

function StatusChip({ net }: { net: number }) {
  if (Math.abs(net) < 0.01) {
    return (
      <span
        className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
        style={{ background: "var(--panel-bg)", color: "var(--ink-muted)" }}
      >
        Balanced
      </span>
    );
  }
  const selling = net > 0;
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium"
      style={{
        background: selling ? "var(--status-good-soft)" : "var(--status-critical-soft)",
        color: selling ? "var(--status-good)" : "var(--status-critical)",
      }}
    >
      <span aria-hidden>{selling ? "▲" : "▼"}</span>
      {selling ? "Selling" : "Buying"}
    </span>
  );
}

export function HouseholdTable({ households }: { households: Household[] }) {
  return (
    <Card
      title="Households"
      subtitle={`${households.length} homes in the neighborhood`}
      icon={<HomeIcon className="h-4 w-4" />}
    >
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr style={{ color: "var(--ink-muted)" }}>
              <th className="pb-2 font-medium">ID</th>
              <th className="pb-2 font-medium">Name</th>
              <th className="pb-2 font-medium">Solar</th>
              <th className="pb-2 pr-2 text-right font-medium">Gen (kWh)</th>
              <th className="pb-2 pr-2 text-right font-medium">Cons (kWh)</th>
              <th className="pb-2 pr-2 text-right font-medium">Net (kWh)</th>
              <th className="pb-2 text-right font-medium">Status</th>
            </tr>
          </thead>
          <tbody className="tabular-nums" style={{ color: "var(--ink)" }}>
            {households.map((h) => {
              const net = h.current_generation_kwh - h.current_consumption_kwh;
              return (
                <tr key={h.id} className="border-t" style={{ borderColor: "var(--grid-line)" }}>
                  <td className="py-2">{h.id}</td>
                  <td className="py-2">{h.name}</td>
                  <td className="py-2">{h.has_solar ? "Yes" : "No"}</td>
                  <td className="py-2 pr-2 text-right">{h.current_generation_kwh.toFixed(2)}</td>
                  <td className="py-2 pr-2 text-right">{h.current_consumption_kwh.toFixed(2)}</td>
                  <td className="py-2 pr-2 text-right">{net.toFixed(2)}</td>
                  <td className="py-2 text-right">
                    <StatusChip net={net} />
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
