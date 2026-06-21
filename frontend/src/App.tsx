import { useEffect, useRef, useState } from "react";
import { fetchBuses, fetchTimeRange, type Filters } from "./api";
import { useAsync } from "./hooks";
import { FilterBar } from "./components/FilterBar";
import { KpiCards } from "./components/KpiCards";
import { TrendChart } from "./components/TrendChart";
import { DistributionChart } from "./components/DistributionChart";
import "./App.css";

// "YYYY-MM-DDTHH:MM" (UTC) for <input type="datetime-local">.
function toInput(iso: string): string {
  return iso.slice(0, 16);
}

export default function App() {
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
      <h1>Telemetry Analytics Dashboard</h1>
      <FilterBar buses={buses ?? []} filters={filters} onChange={setFilters} />
      <KpiCards filters={filters} />
      <div className="charts">
        <TrendChart filters={filters} buses={buses ?? []} />
        <DistributionChart filters={filters} />
      </div>
    </div>
  );
}
