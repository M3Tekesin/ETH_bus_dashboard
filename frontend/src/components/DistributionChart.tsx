import { useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer,
} from "recharts";
import { fetchDistribution, type Filters } from "../api";
import { useAsync } from "../hooks";

const METRICS = [
  { key: "speed", label: "Speed (km/h)" },
  { key: "temp", label: "Temperature (°C)" },
  { key: "power", label: "Power (kW)" },
];

const fmt = (v: number | null) => (v === null ? "—" : v.toFixed(1));

export function DistributionChart({ filters }: { filters: Filters }) {
  const [metric, setMetric] = useState("speed");
  const { data, loading, error } = useAsync(
    () => fetchDistribution(filters, metric, 20),
    [filters.bus, filters.start, filters.end, metric]
  );

  const metricLabel = METRICS.find((m) => m.key === metric)?.label ?? metric;

  // x-axis label is each bin's lower edge (one decimal); the tooltip shows the
  // full lower–upper span. One decimal keeps the labels unique for narrow-range
  // metrics such as temperature, where whole-number labels would collide.
  const bars = (data?.bins ?? []).map((b) => ({
    bin: b.lower.toFixed(1),
    range: `${b.lower.toFixed(1)} – ${b.upper.toFixed(1)}`,
    count: b.count,
  }));

  return (
    <div className="card">
      <div className="card-head">
        <h2>Distribution</h2>
        <select value={metric} onChange={(e) => setMetric(e.target.value)}>
          {METRICS.map((m) => <option key={m.key} value={m.key}>{m.label}</option>)}
        </select>
      </div>
      {error && <div className="error">{error}</div>}
      {loading ? <p>Loading…</p> : (
        <>
          <ResponsiveContainer width="100%" height={290}>
            <BarChart data={bars} margin={{ top: 5, right: 10, bottom: 24, left: 12 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="bin"
                tick={{ fontSize: 10 }}
                minTickGap={12}
                label={{ value: metricLabel, position: "insideBottom", offset: -12, fontSize: 12 }}
              />
              <YAxis
                tick={{ fontSize: 10 }}
                label={{ value: "count (samples)", angle: -90, position: "insideLeft", fontSize: 12 }}
              />
              <Tooltip
                formatter={(value) => [value as number, "samples"]}
                labelFormatter={(_label, payload) =>
                  payload && payload.length
                    ? `${metricLabel}: ${payload[0].payload.range}`
                    : ""
                }
              />
              <Bar dataKey="count" fill="#10b981" name="samples" />
            </BarChart>
          </ResponsiveContainer>
          <div className="quartiles">
            <span>min {fmt(data?.min ?? null)}</span>
            <span>Q1 {fmt(data?.q1 ?? null)}</span>
            <span>median {fmt(data?.median ?? null)}</span>
            <span>Q3 {fmt(data?.q3 ?? null)}</span>
            <span>max {fmt(data?.max ?? null)}</span>
          </div>
        </>
      )}
    </div>
  );
}
