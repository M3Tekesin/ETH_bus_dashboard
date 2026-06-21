import { fetchKpis, type Filters } from "../api";
import { useAsync } from "../hooks";

const fmt = (v: number | null | undefined, digits = 1) =>
  v === null || v === undefined ? "—" : v.toFixed(digits);

export function KpiCards({ filters }: { filters: Filters }) {
  const { data, loading, error } = useAsync(() => fetchKpis(filters),
    [filters.bus, filters.start, filters.end]);

  if (error) return <div className="error">KPI error: {error}</div>;
  const k = data;
  const cards = [
    ["Avg Speed", `${fmt(k?.avg_speed_kmh)} km/h`],
    ["Max Temp", `${fmt(k?.max_temp_c)} °C`],
    ["Total Energy", `${fmt(k?.total_energy_kwh)} kWh`],
    ["Distance", `${fmt(k?.distance_km)} km`],
  ];
  return (
    <div className="kpis">
      {cards.map(([label, value]) => (
        <div className="kpi" key={label}>
          <div className="kpi-label">{label}</div>
          <div className="kpi-value">{loading ? "…" : value}</div>
        </div>
      ))}
    </div>
  );
}
