/**
 * Production (Vercel): set VITE_ENGINE_URL to your reachable Engine base, e.g.
 *   https://xxxx.ngrok-free.app
 * Dev: leave unset — Vite proxy forwards /health, /backtest, /market to localhost:8000.
 */
export function engineUrl(path: string): string {
  const raw = import.meta.env.VITE_ENGINE_URL as string | undefined;
  const base = (raw ?? "").trim().replace(/\/$/, "");
  if (!base) return path.startsWith("/") ? path : `/${path}`;
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${base}${p}`;
}
