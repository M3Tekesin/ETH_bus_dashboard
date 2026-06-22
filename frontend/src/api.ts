const BASE = "http://localhost:8000/api";
const TOKEN_KEY = "telemetry_token";

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (t: string) => localStorage.setItem(TOKEN_KEY, t);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

// Log in and store the JWT. Throws on bad credentials.
export async function login(username: string, password: string): Promise<void> {
  const r = await fetch(`${BASE}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!r.ok) throw new Error(r.status === 401 ? "Invalid username or password" : `Login failed (${r.status})`);
  const body = (await r.json()) as { access_token: string };
  setToken(body.access_token);
}

export interface Filters { bus?: string; start?: string; end?: string; }

export interface Kpis {
  avg_speed_kmh: number | null;
  max_speed_kmh: number | null;
  max_temp_c: number | null;
  total_energy_kwh: number | null;
  distance_km: number | null;
  avg_passengers: number | null;
  max_passengers: number | null;
  sample_count: number;
}
export interface TimeRange { min: string | null; max: string | null; }
export interface TrendPoint { bucket: string; value: number | null; }
export interface TrendByBusPoint { bucket: string; bus_id: string; value: number | null; }
export interface DistributionBin { lower: number; upper: number; count: number; }
export interface Distribution {
  bins: DistributionBin[];
  min: number | null; q1: number | null; median: number | null;
  q3: number | null; max: number | null;
}

function toUtcIso(v: string): string {
  // datetime-local values are zoneless; the dataset is UTC, so the picked
  // wall-clock time is interpreted as UTC (the inputs are labelled accordingly).
  const base = v.length === 16 ? `${v}:00` : v;
  const d = new Date(`${base}Z`);
  return isNaN(d.getTime()) ? v : d.toISOString();
}

function qs(f: Filters, extra: Record<string, string> = {}): string {
  const p = new URLSearchParams();
  if (f.bus) p.set("bus", f.bus);
  if (f.start) p.set("start", toUtcIso(f.start));
  if (f.end) p.set("end", toUtcIso(f.end));
  for (const [k, v] of Object.entries(extra)) p.set(k, v);
  const s = p.toString();
  return s ? `?${s}` : "";
}

async function get<T>(path: string): Promise<T> {
  const token = getToken();
  const r = await fetch(`${BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (r.status === 401) {
    // Token missing/expired — drop it and let the app return to the login screen.
    clearToken();
    window.dispatchEvent(new Event("auth-expired"));
    throw new Error("Session expired — please log in again");
  }
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json() as Promise<T>;
}

export const fetchBuses = () => get<string[]>("/buses");
export const fetchTimeRange = (bus?: string) =>
  get<TimeRange>(`/time-range${bus ? `?bus=${encodeURIComponent(bus)}` : ""}`);
export const fetchKpis = (f: Filters) => get<Kpis>(`/kpis${qs(f)}`);
export const fetchTrend = (f: Filters, metric: string, bucket = 300) =>
  get<TrendPoint[]>(`/trend${qs(f, { metric, bucket: String(bucket) })}`);
export const fetchTrendByBus = (
  f: Filters, metric: string, bucket = 300, buses: string[] = []
) => {
  // Compare mode ignores the single-bus filter; pass time range + chosen buses.
  const extra: Record<string, string> = { metric, bucket: String(bucket) };
  if (buses.length) extra.buses = buses.join(",");
  return get<TrendByBusPoint[]>(
    `/trend-by-bus${qs({ start: f.start, end: f.end }, extra)}`
  );
};
export const fetchDistribution = (f: Filters, metric: string, bins = 20) =>
  get<Distribution>(`/distribution${qs(f, { metric, bins: String(bins) })}`);
