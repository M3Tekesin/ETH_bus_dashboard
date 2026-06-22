import { useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer,
  ReferenceLine, Legend,
} from "recharts";
import { fetchTrend, fetchTrendByBus, type Filters } from "../api";
import { useAsync } from "../hooks";

const METRICS = [
  { key: "speed", label: "Speed (km/h)" },
  { key: "temp", label: "Temperature (°C)" },
  { key: "power", label: "Power (kW)" },
];

const CONSUMPTION = "#4f46e5"; // positive: drawing power
const RECOVERY = "#10b981"; // negative: regenerative braking
// Per-bus colors for compare mode.
const BUS_COLORS = ["#4f46e5", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6", "#06b6d4"];

// Compare mode uses a real time axis so overlaid buses line up by timestamp.
// The trend bucket is 5 minutes; if two consecutive samples for a bus are more
// than ~2 buckets apart there's a data gap (e.g. between mission days), so we
// insert a null breaker to stop the line bridging time with no data.
type Row = Record<string, number | string | null>;

// Pick a bucket size from the selected span. Capped at 1 hour so each mission
// keeps several points and renders as a line (never collapses to a lone dot);
// a narrow range keeps full 5-minute detail.
function pickBucketSeconds(spanMs: number | null): number {
  if (spanMs == null) return 300;
  const days = spanMs / 86_400_000;
  return days <= 2 ? 300 : 3600;
}

// First timestamp of each distinct (local) day among the rows that carry data,
// for drawing day-separator lines. Returns [] if there are too many to be
// legible. `ts` reads the x value from a row.
function dayStarts<T>(rows: T[], ts: (r: T) => number, hasData: (r: T) => boolean): number[] {
  const starts: number[] = [];
  let prevDay = "";
  for (const r of rows) {
    if (!hasData(r)) continue;
    const day = new Date(ts(r)).toLocaleDateString();
    if (day !== prevDay) { starts.push(ts(r)); prevDay = day; }
  }
  const transitions = starts.slice(1); // skip the very first day (chart start)
  return transitions.length <= 31 ? transitions : [];
}

function spanMsOf(start?: string, end?: string): number | null {
  if (!start || !end) return null;
  const norm = (v: string) => Date.parse(v.length === 16 ? `${v}:00Z` : `${v}Z`);
  const s = norm(start);
  const e = norm(end);
  return isNaN(s) || isNaN(e) ? null : e - s;
}

// Multiple buses → merged rows keyed by ts, each bus its own key, with per-bus
// null breakers in gaps (more than ~2 buckets apart) so each line only spans
// real data.
function multiSeries(
  data: { bucket: string; bus_id: string; value: number | null }[],
  selected: string[],
  bucketMs: number,
): Row[] {
  const gapMs = bucketMs * 2;
  const rows = new Map<number, Row>();
  const at = (ts: number): Row => {
    let r = rows.get(ts);
    if (!r) { r = { ts }; rows.set(ts, r); }
    return r;
  };
  for (const bus of selected) {
    const pts = data
      .filter((p) => p.bus_id === bus)
      .sort((a, b) => (a.bucket < b.bucket ? -1 : 1));
    let prevTs: number | null = null;
    for (const p of pts) {
      const ts = new Date(p.bucket).getTime();
      if (prevTs != null && ts - prevTs > gapMs) {
        at(prevTs + bucketMs)[bus] = null;
      }
      at(ts)[bus] = p.value;
      prevTs = ts;
    }
  }
  return Array.from(rows.values()).sort((a, b) => (a.ts as number) - (b.ts as number));
}

const fmtTime = (ts: number) => new Date(ts).toLocaleString();

export function TrendChart({ filters, buses }: { filters: Filters; buses: string[] }) {
  const [metric, setMetric] = useState("speed");
  const [compare, setCompare] = useState(false);
  // Which buses to overlay in compare mode. `null` = not yet chosen → all buses.
  const [picked, setPicked] = useState<string[] | null>(null);

  const metricLabel = METRICS.find((m) => m.key === metric)?.label ?? metric;
  const selected = picked ?? buses;

  const togglePick = (bus: string) => {
    const base = picked ?? buses;
    setPicked(base.includes(bus) ? base.filter((b) => b !== bus) : [...base, bus]);
  };

  const single = useAsync(
    () => fetchTrend(filters, metric, 300),
    [filters.bus, filters.start, filters.end, metric, compare]
  );
  // Coarsen the bucket as the time span grows so a months-wide compare view
  // doesn't squeeze each mission into an unreadable spike.
  const bucketSeconds = pickBucketSeconds(spanMsOf(filters.start, filters.end));
  const multi = useAsync(
    () =>
      compare && selected.length
        ? fetchTrendByBus(filters, metric, bucketSeconds, selected)
        : Promise.resolve([]),
    [filters.start, filters.end, metric, compare, selected.join(","), bucketSeconds]
  );

  const loading = compare ? multi.loading : single.loading;
  const error = compare ? multi.error : single.error;

  // Single mode: categorical x-axis, one slot per bucket.
  const points = (single.data ?? []).map((p) => ({
    t: new Date(p.bucket).toLocaleString(),
    value: p.value,
  }));

  // Compare mode: time-scaled, gap-aware rows for the selected buses only.
  const selectedSet = new Set(selected);
  const compareRows = multiSeries(
    (multi.data ?? []).filter((p) => selectedSet.has(p.bus_id)),
    selected,
    bucketSeconds * 1000
  );

  // Vertical separators at the start of each distinct day, so days are easy to
  // tell apart. Compare mode keys off the time axis (ts); single mode keys off
  // the categorical label. Suppressed when there would be too many to read.
  const compareDayLines = dayStarts(
    compareRows,
    (r) => r.ts as number,
    (r) => selected.some((b) => typeof r[b] === "number"),
  );
  const singleDayLines = ((): string[] => {
    const starts: string[] = [];
    let prevDay = "";
    for (const p of single.data ?? []) {
      const d = new Date(p.bucket);
      const day = d.toLocaleDateString();
      if (day !== prevDay) { starts.push(d.toLocaleString()); prevDay = day; }
    }
    const transitions = starts.slice(1); // skip the very first day (chart start)
    return transitions.length <= 31 ? transitions : [];
  })();
  const dayLines: (number | string)[] = compare ? compareDayLines : singleDayLines;

  // Zero-split coloring (single mode only — keeps power consumption vs regen clear).
  let min = Infinity;
  let max = -Infinity;
  for (const p of points) {
    if (p.value == null) continue;
    if (p.value < min) min = p.value;
    if (p.value > max) max = p.value;
  }
  const hasNegative = !compare && min < 0;
  const zeroOffset = max <= 0 ? 0 : min >= 0 ? 1 : max / (max - min);

  return (
    <div className="card">
      <div className="card-head">
        <h2>Trend over time</h2>
        <div className="card-controls">
          <label className="toggle">
            <input type="checkbox" checked={compare}
                   onChange={(e) => setCompare(e.target.checked)} />
            Compare buses
          </label>
          <select value={metric} onChange={(e) => setMetric(e.target.value)}>
            {METRICS.map((m) => <option key={m.key} value={m.key}>{m.label}</option>)}
          </select>
        </div>
      </div>
      {compare && (
        <div className="bus-picker">
          {buses.map((bus, i) => (
            <label key={bus} className="toggle">
              <input
                type="checkbox"
                checked={selected.includes(bus)}
                onChange={() => togglePick(bus)}
              />
              <i style={{ background: BUS_COLORS[i % BUS_COLORS.length] }} />
              {bus}
            </label>
          ))}
          {selected.length === 0 && <span className="muted">select at least one bus</span>}
        </div>
      )}
      {error && <div className="error">{error}</div>}
      {loading ? <p>Loading…</p> : (
        <ResponsiveContainer width="100%" height={300}>
          <LineChart
            data={(compare ? compareRows : points) as Row[]}
            margin={{ top: 5, right: 10, bottom: 5, left: 12 }}
          >
            {!compare && (
              <defs>
                <linearGradient id="trendSplit" x1="0" y1="0" x2="0" y2="1">
                  <stop offset={zeroOffset} stopColor={CONSUMPTION} />
                  <stop offset={zeroOffset} stopColor={RECOVERY} />
                </linearGradient>
              </defs>
            )}
            <CartesianGrid strokeDasharray="3 3" />
            {compare ? (
              <XAxis
                dataKey="ts"
                type="number"
                scale="time"
                domain={["dataMin", "dataMax"]}
                tickFormatter={fmtTime}
                tick={{ fontSize: 10 }}
                minTickGap={40}
              />
            ) : (
              <XAxis dataKey="t" tick={{ fontSize: 10 }} minTickGap={40} />
            )}
            <YAxis
              tick={{ fontSize: 10 }}
              label={{ value: metricLabel, angle: -90, position: "insideLeft", fontSize: 12 }}
            />
            <Tooltip
              labelFormatter={(label) => (compare ? fmtTime(label as number) : String(label))}
              formatter={(value, name) => [value as number, compare ? name : metricLabel]}
            />
            {hasNegative && <ReferenceLine y={0} stroke="#888" strokeDasharray="4 4" />}
            {dayLines.map((x, i) => (
              <ReferenceLine key={`day-${i}`} x={x} stroke="#c7cdd6" strokeDasharray="2 4" />
            ))}
            {compare ? (
              <>
                <Legend />
                {selected.map((bus) => (
                  <Line
                    key={bus}
                    type="monotone"
                    dataKey={bus}
                    name={bus}
                    stroke={BUS_COLORS[buses.indexOf(bus) % BUS_COLORS.length]}
                    dot={false}
                  />
                ))}
              </>
            ) : (
              <Line
                type="monotone"
                dataKey="value"
                stroke={hasNegative ? "url(#trendSplit)" : CONSUMPTION}
                dot={false}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      )}
      {!compare && metric === "power" && (
        <div className="legend">
          <span><i style={{ background: CONSUMPTION }} /> consumption (&gt; 0)</span>
          <span><i style={{ background: RECOVERY }} /> recovered · regen braking (&lt; 0)</span>
        </div>
      )}
    </div>
  );
}
