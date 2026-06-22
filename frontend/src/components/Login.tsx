import { useState } from "react";
import { login } from "../api";

export function Login({ onAuthed }: { onAuthed: () => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(username, password);
      onAuthed();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login">
      <form className="login-card" onSubmit={submit}>
        <h1>Telemetry Dashboard</h1>
        <p className="muted">Sign in to continue</p>
        <label>
          Username
          <input value={username} onChange={(e) => setUsername(e.target.value)}
                 autoFocus autoComplete="username" />
        </label>
        <label>
          Password
          <input type="password" value={password}
                 onChange={(e) => setPassword(e.target.value)}
                 autoComplete="current-password" />
        </label>
        {error && <div className="error">{error}</div>}
        <button type="submit" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
