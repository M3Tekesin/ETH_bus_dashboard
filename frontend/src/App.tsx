import { useEffect, useRef, useState } from "react";
import { clearToken, fetchBuses, fetchTimeRange, getToken, type Filters } from "./api";
import { useAsync } from "./hooks";
import { FilterBar } from "./components/FilterBar";
import { KpiCards } from "./components/KpiCards";
import { TrendChart } from "./components/TrendChart";
import { DistributionChart } from "./components/DistributionChart";
import { Login } from "./components/Login";
import "./App.css";

// "YYYY-MM-DDTHH:MM" (UTC) for <input type="datetime-local">.
function toInput(iso: string): string {
  return iso.slice(0, 16);
}

export default function App() {
  const [authed, setAuthed] = useState(() => !!getToken());

  // A 401 anywhere clears the token and fires this event; return to login.
  useEffect(() => {
    const onExpired = () => setAuthed(false);
    window.addEventListener("auth-expired", onExpired);
    return () => window.removeEventListener("auth-expired", onExpired);
  }, []);

  if (!authed) return <Login onAuthed={() => setAuthed(true)} />;
  return <Dashboard onLogout={() => { clearToken(); setAuthed(false); }} />;
}

function Dashboard({ onLogout }: { onLogout: () => void }) {
  const [filters, setFilters] = useState<Filters>({});
  const { data: buses } = useAsync(() => fetchBuses(), []);
  const defaulted = useRef(false);

  // On first load, default to one bus + its most recent day of data instead of
  // querying all buses / all time. Keeps the initial render small and fast at
  // scale; the user can clear filters to widen the view.
  useEffect(() => {
    if (defaulted.current || !buses || buses.length === 0) return;
    defaulted.current = true;
    const bus = buses[0];
    fetchTimeRange(bus)
      .then((tr) => {
        if (!tr.max) {
          setFilters({ bus });
          return;
        }
        const end = new Date(tr.max);
        const start = new Date(end.getTime() - 24 * 60 * 60 * 1000);
        setFilters({
          bus,
          start: toInput(start.toISOString()),
          end: toInput(end.toISOString()),
        });
      })
      .catch(() => setFilters({ bus }));
  }, [buses]);

  return (
    <div className="app">
      <div className="app-head">
        <h1>Telemetry Analytics Dashboard</h1>
        <button className="logout" onClick={onLogout}>Log out</button>
      </div>
      <FilterBar buses={buses ?? []} filters={filters} onChange={setFilters} />
      <KpiCards filters={filters} />
      <div className="charts">
        <TrendChart filters={filters} buses={buses ?? []} />
        <DistributionChart filters={filters} />
      </div>
    </div>
  );
}
