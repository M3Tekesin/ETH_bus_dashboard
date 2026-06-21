import type { Filters } from "../api";

interface Props {
  buses: string[];
  filters: Filters;
  onChange: (f: Filters) => void;
}

export function FilterBar({ buses, filters, onChange }: Props) {
  const set = (patch: Partial<Filters>) => onChange({ ...filters, ...patch });
  const chips: [keyof Filters, string][] = [];
  if (filters.bus) chips.push(["bus", `Bus: ${filters.bus}`]);
  if (filters.start) chips.push(["start", `From: ${filters.start}`]);
  if (filters.end) chips.push(["end", `To: ${filters.end}`]);

  return (
    <div className="filterbar">
      <label>
        Bus:
        <select value={filters.bus ?? ""}
                onChange={(e) => set({ bus: e.target.value || undefined })}>
          <option value="">All</option>
          {buses.map((b) => <option key={b} value={b}>{b}</option>)}
        </select>
      </label>
      <label>From (UTC):
        <input type="datetime-local" value={filters.start ?? ""}
               onChange={(e) => set({ start: e.target.value || undefined })} />
      </label>
      <label>To (UTC):
        <input type="datetime-local" value={filters.end ?? ""}
               onChange={(e) => set({ end: e.target.value || undefined })} />
      </label>
      <div className="chips">
        {chips.length === 0 && <span className="chip muted">No filters</span>}
        {chips.map(([key, label]) => (
          <span key={key} className="chip">
            {label}
            <button onClick={() => set({ [key]: undefined } as Partial<Filters>)}>×</button>
          </span>
        ))}
      </div>
    </div>
  );
}
