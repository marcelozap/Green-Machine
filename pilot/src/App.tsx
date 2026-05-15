import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AreaSeries,
  ColorType,
  createChart,
  CrosshairMode,
  type IChartApi,
  type ISeriesApi,
} from "lightweight-charts";
import { engineUrl } from "./engineUrl";

type EquityPoint = [string, number];

type SimilarDay = {
  trade_date: string;
  vix_close: number | null;
  distance: number;
};

type LiveEvent = {
  t: string;
  kind: string;
  text?: string;
  file?: string;
  bytes?: number;
  ingest_kind?: string;
  path?: string;
  error?: string;
  stderr?: string;
  code?: number;
};

type DeskLogItem = {
  id: number;
  ts: string;
  kind: "note" | "trade";
  symbol?: string | null;
  description?: string | null;
  tags?: string[];
  session_date?: string | null;
  text?: string | null;
};

type SessionBudget = {
  available: false;
} | {
  available: true;
  last_session: {
    date: string;
    pnl: number;
    lots: number;
    cum_pnl: number;
    is_today: boolean;
  };
  total_realized_pnl: number;
  daily_budget_usd: number;
  headroom_usd: number | null;
  session_over_budget: boolean;
  zero_dte_pct: number;
  zero_dte_pnl: number;
};

function formatLiveLine(e: LiveEvent): string {
  const ts = e.t?.slice(11, 19) ?? "??:??:??";
  switch (e.kind) {
    case "note":
      return `${ts}  NOTE  ${e.text ?? ""}`;
    case "ingest_queued":
      return `${ts}  UPLOAD  ${e.file ?? "?"} · ${e.ingest_kind ?? "?"} (${((e.bytes ?? 0) / 1024).toFixed(1)} KB)`;
    case "ingest_done":
      return `${ts}  DONE  ${e.ingest_kind ?? "?"} ingested`;
    case "ingest_error":
      return `${ts}  ERR  ${e.ingest_kind ?? "?"} — ${(e.error ?? e.stderr ?? "failed").toString().slice(0, 120)}`;
    default:
      return `${ts}  ${e.kind}`;
  }
}

type BacktestResponse = {
  equity_curve: EquityPoint[];
  sharpe: number | null;
  sortino: number | null;
  calmar: number | null;
  max_drawdown: number;
  total_return: number;
  circuit_breaker_hit: boolean;
  notes: string;
  similar_days?: SimilarDay[];
  llm_summary?: string | null;
  bs_delta_mae?: number | null;
};

const ACCENT = "#39FF14";
const GHOST = "#F8F8FF";
const PANEL = "rgba(8,8,8,0.92)";

function useHotkey(key: string, meta: boolean, on: () => void) {
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() !== key.toLowerCase()) return;
      if (meta && !(e.metaKey || e.ctrlKey)) return;
      e.preventDefault();
      on();
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [key, meta, on]);
}

function ChartPane({ data }: { data: EquityPoint[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const chart = createChart(el, {
      layout: {
        background: { type: ColorType.Solid, color: "#050505" },
        textColor: GHOST,
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "rgba(57,255,20,0.06)" },
        horzLines: { color: "rgba(248,248,255,0.06)" },
      },
      crosshair: { mode: CrosshairMode.Magnet },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false },
      localization: { locale: "en-US" },
    });
    const series = chart.addSeries(AreaSeries, {
      lineColor: ACCENT,
      topColor: "rgba(57,255,20,0.35)",
      bottomColor: "rgba(5,5,5,0)",
      lineWidth: 2,
      priceLineVisible: false,
    });
    chartRef.current = chart;
    seriesRef.current = series;

    const ro = new ResizeObserver(() => {
      chart.applyOptions({ width: el.clientWidth, height: el.clientHeight });
    });
    ro.observe(el);
    chart.applyOptions({ width: el.clientWidth, height: el.clientHeight });

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    const series = seriesRef.current;
    if (!series || data.length === 0) return;
    series.setData(
      data.map(([t, v]) => ({
        time: t.slice(0, 10) as `${number}-${number}-${number}`,
        value: v,
      })),
    );
    chartRef.current?.timeScale().fitContent();
  }, [data]);

  return <div ref={ref} className="h-full min-h-[320px] w-full" />;
}

export default function App() {
  const [snapshot, setSnapshot] = useState({ spy: "—", vix: "—", asOf: "—" });
  const [pulse, setPulse] = useState(true);
  const [liveEvents, setLiveEvents] = useState<LiveEvent[]>([]);
  const [deskNote, setDeskNote] = useState("");
  const [uploadKind, setUploadKind] = useState<"tos_daily" | "options">("tos_daily");
  const [uploadBusy, setUploadBusy] = useState(false);
  const [equity, setEquity] = useState<EquityPoint[]>([]);
  const [stats, setStats] = useState<BacktestResponse | null>(null);
  const [sidebar, setSidebar] = useState(
    "## Strategy terminal\n\nAwaiting command. Use **⌘K** / **Ctrl+K** to run a backtest.\n",
  );
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [cmd, setCmd] = useState("");

  // Session budget rail
  const [budget, setBudget] = useState<SessionBudget>({ available: false });

  useEffect(() => {
    void (async () => {
      try {
        const res = await fetch(engineUrl("/desk/session-budget"));
        if (res.ok) setBudget((await res.json()) as SessionBudget);
      } catch { /* offline */ }
    })();
  }, []);

  // Trade logging state
  const [tradeSymbol, setTradeSymbol] = useState("");
  const [tradeLine, setTradeLine] = useState("");
  const [tradeOpen, setTradeOpen] = useState(true);
  const [tradeBusy, setTradeBusy] = useState(false);
  const [tradeToast, setTradeToast] = useState(false);
  const [deskTimeline, setDeskTimeline] = useState<DeskLogItem[]>([]);
  const [micActive, setMicActive] = useState(false);
  const recognitionRef = useRef<{ stop: () => void } | null>(null);

  const loadDeskTimeline = useCallback(async () => {
    try {
      const res = await fetch(engineUrl("/desk/timeline?limit=40"));
      if (res.ok) {
        const j = (await res.json()) as DeskLogItem[];
        setDeskTimeline(j);
      }
    } catch {
      /* offline */
    }
  }, []);

  useEffect(() => {
    void loadDeskTimeline();
  }, [loadDeskTimeline]);

  const postDeskTrade = useCallback(async () => {
    const sym = tradeSymbol.trim().toUpperCase();
    const line = tradeLine.trim();
    if (!sym || !line) return;
    setTradeBusy(true);
    try {
      const tags = tradeOpen ? ["open"] : ["closed"];
      const res = await fetch(engineUrl("/desk/trade"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol: sym, description: line, tags }),
      });
      if (res.ok) {
        setTradeSymbol("");
        setTradeLine("");
        setTradeOpen(true);
        void loadDeskTimeline();
        setTradeToast(true);
        setTimeout(() => setTradeToast(false), 4000);
      }
    } catch {
      /* offline */
    } finally {
      setTradeBusy(false);
    }
  }, [tradeSymbol, tradeLine, tradeOpen, loadDeskTimeline]);

  const toggleMic = useCallback(() => {
    if (micActive) {
      recognitionRef.current?.stop();
      setMicActive(false);
      return;
    }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const SR = (window as any).SpeechRecognition ?? (window as any).webkitSpeechRecognition;
    if (!SR) return;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const r = new SR() as any;
    r.continuous = false;
    r.interimResults = false;
    r.onresult = (ev: { results: { [k: number]: { [k: number]: { transcript: string } } } }) => {
      const t = ev.results[0]?.[0]?.transcript ?? "";
      setTradeLine((prev) => (prev ? `${prev} ${t}` : t));
      setMicActive(false);
    };
    r.onerror = () => setMicActive(false);
    r.onend = () => setMicActive(false);
    recognitionRef.current = r as { stop: () => void };
    r.start();
    setMicActive(true);
  }, [micActive]);

  const runBacktest = useCallback(async (prompt: string) => {
    setSidebar((s) => s + `\n> ${prompt}\n`);
    const res = await fetch(engineUrl("/backtest/llm"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, config: null }),
    });
    if (!res.ok) {
      setSidebar((s) => s + `\n*error* \`${res.status}\` — is the API up?\n`);
      return;
    }
    const body = (await res.json()) as BacktestResponse;
    setEquity(body.equity_curve);
    setStats(body);
    const sim =
      body.similar_days?.length ?
        `\n**Similar regimes:** ${body.similar_days
          .slice(0, 6)
          .map((d) => `${d.trade_date} (VIX ${d.vix_close?.toFixed(1) ?? "—"})`)
          .join(" · ")}\n`
        : "";
    const llm = body.llm_summary ? `\n_${body.llm_summary}_\n` : "";
    const bs =
      body.bs_delta_mae != null && !Number.isNaN(body.bs_delta_mae)
        ? `\nBS Δ MAE: ${body.bs_delta_mae.toFixed(4)}\n`
        : "";
    setSidebar(
      (s) =>
        s +
        llm +
        sim +
        bs +
        `\n**PnL curve updated.** Sharpe: ${body.sharpe?.toFixed(2) ?? "n/a"} · ` +
        `Max DD: ${(body.max_drawdown * 100).toFixed(2)}% · ` +
        `Circuit: ${body.circuit_breaker_hit ? "TRIP" : "OK"}\n`,
    );
  }, []);

  useHotkey("k", true, () => setPaletteOpen(true));

  useEffect(() => {
    const id = window.setInterval(() => setPulse((p) => !p), 900);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        const h = await fetch(engineUrl("/health"));
        if (!h.ok) return;
        const m = await fetch(engineUrl("/market/snapshot"));
        if (!m.ok) return;
        const j = (await m.json()) as { spy: number | null; vix: number | null; as_of?: string | null };
        setSnapshot({
          spy: j.spy != null ? j.spy.toFixed(2) : "—",
          vix: j.vix != null ? j.vix.toFixed(2) : "—",
          asOf: j.as_of ?? "—",
        });
      } catch {
        /* cockpit still usable offline */
      }
    })();
  }, []);

  useEffect(() => {
    const url = engineUrl("/live/stream");
    const es = new EventSource(url);
    es.onmessage = (ev) => {
      try {
        const j = JSON.parse(ev.data) as {
          snapshot?: { spy: number | null; vix: number | null; as_of?: string | null };
          events?: LiveEvent[];
        };
        if (j.snapshot) {
          setSnapshot({
            spy: j.snapshot.spy != null ? Number(j.snapshot.spy).toFixed(2) : "—",
            vix: j.snapshot.vix != null ? Number(j.snapshot.vix).toFixed(2) : "—",
            asOf:
              j.snapshot.as_of != null && j.snapshot.as_of !== ""
                ? String(j.snapshot.as_of).slice(0, 10)
                : "—",
          });
        }
        if (j.events?.length) setLiveEvents(j.events);
      } catch {
        /* ignore malformed SSE frames */
      }
    };
    return () => es.close();
  }, []);

  const postDeskNote = useCallback(async () => {
    const t = deskNote.trim();
    if (!t) return;
    try {
      const res = await fetch(engineUrl("/live/note"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: t }),
      });
      if (res.ok) setDeskNote("");
    } catch {
      /* offline */
    }
  }, [deskNote]);

  const onUploadCsv = useCallback(
    async (fileList: FileList | null) => {
      const f = fileList?.[0];
      if (!f) return;
      setUploadBusy(true);
      try {
        const fd = new FormData();
        fd.append("file", f);
        const res = await fetch(engineUrl(`/ingest/eod?kind=${uploadKind}`), {
          method: "POST",
          body: fd,
        });
        if (!res.ok) {
          setSidebar((s) => s + `\n*upload* HTTP ${res.status}\n`);
        }
      } catch {
        setSidebar((s) => s + "\n*upload* network error — is the Engine up?\n");
      } finally {
        setUploadBusy(false);
      }
    },
    [uploadKind],
  );

  const metrics = useMemo(() => {
    if (!stats) return "—";
    return [
      `Sharpe ${stats.sharpe?.toFixed(2) ?? "n/a"}`,
      `Sortino ${stats.sortino?.toFixed(2) ?? "n/a"}`,
      `Calmar ${stats.calmar?.toFixed(2) ?? "n/a"}`,
      stats.bs_delta_mae != null ? `Δ MAE ${stats.bs_delta_mae.toFixed(3)}` : null,
    ]
      .filter(Boolean)
      .join("  ·  ");
  }, [stats]);

  return (
    <div className="flex min-h-screen flex-col">
      <header
        className="flex items-center justify-between border-b px-6 py-3"
        style={{ borderColor: "rgba(57,255,20,0.15)", background: PANEL }}
      >
        <div className="font-mono text-xs tracking-[0.35em] text-[#39FF14]">GREEN MACHINE</div>
        <div className="flex flex-wrap items-center gap-x-8 gap-y-1 font-mono text-sm text-[#F8F8FF]">
          <span>
            SPY <span className="text-[#39FF14]">{snapshot.spy}</span>
          </span>
          <span>
            VIX <span className="text-[#39FF14]">{snapshot.vix}</span>
          </span>
          <span className="text-[11px] text-[#F8F8FF]/45" title="Last bar in vault (EOD CSV)">
            TAPE <span className="text-[#F8F8FF]/70">{snapshot.asOf}</span>
          </span>
          <span className="flex items-center gap-2">
            <span
              className="inline-block h-2 w-2 rounded-full"
              style={{
                background: pulse ? "#39FF14" : "#1a5c12",
                boxShadow: pulse ? "0 0 12px #39FF14" : "none",
              }}
            />
            SYS
          </span>
        </div>
      </header>

      <div className="grid flex-1 grid-cols-1 gap-0 lg:grid-cols-[1fr_340px]">
        <main className="flex flex-col border-r border-[rgba(57,255,20,0.08)]">
          <div className="border-b border-[rgba(57,255,20,0.08)] px-4 py-2 font-mono text-[11px] text-[#F8F8FF]/70">
            CUMULATIVE PnL · {metrics}
          </div>
          <div className="flex-1 p-2">
            <ChartPane data={equity} />
          </div>
        </main>

        {/* ── LIVE DESK ── */}
        <aside
          className="flex max-h-[55vh] flex-col overflow-hidden border-t border-[rgba(57,255,20,0.08)] lg:max-h-none lg:border-t-0"
          style={{ background: PANEL }}
        >
          <div className="shrink-0 overflow-y-auto border-b border-[rgba(57,255,20,0.12)] p-3 font-mono text-[11px]">
            <div className="mb-2 text-[10px] tracking-[0.35em] text-[#39FF14]/85">LIVE DESK</div>

            {/* ── Session budget rail ── */}
            {budget.available && (() => {
              const s = budget.last_session;
              const pnlStr = (s.pnl >= 0 ? "+" : "") + "$" + Math.abs(s.pnl).toFixed(0);
              const ytdStr = (budget.total_realized_pnl >= 0 ? "+" : "−") + "$" + Math.abs(budget.total_realized_pnl).toFixed(0);
              const zeroStr = (budget.zero_dte_pct * 100).toFixed(0) + "%";
              const isRed = s.pnl < 0;
              const overBudget = budget.session_over_budget;
              return (
                <div
                  className={`mb-2 flex flex-wrap gap-x-3 gap-y-0.5 border px-2 py-1 text-[9px] leading-snug ${
                    overBudget
                      ? "border-red-800/60 bg-red-950/30"
                      : "border-[rgba(57,255,20,0.12)] bg-black/20"
                  }`}
                  title={`Budget: −$${budget.daily_budget_usd.toFixed(0)} · 0DTE P&L: −$${Math.abs(budget.zero_dte_pnl).toFixed(0)}`}
                >
                  <span className="text-[#F8F8FF]/45">{s.is_today ? "TODAY" : `TAPE ${s.date.slice(5)}`}</span>
                  <span className={isRed ? "text-red-400" : "text-[#39FF14]"}>{pnlStr}</span>
                  <span className="text-[#F8F8FF]/35">·</span>
                  <span className="text-[#F8F8FF]/45">YTD</span>
                  <span className={budget.total_realized_pnl < 0 ? "text-red-400/80" : "text-[#39FF14]/80"}>{ytdStr}</span>
                  <span className="text-[#F8F8FF]/35">·</span>
                  <span className="text-[#F8F8FF]/45">0DTE</span>
                  <span className={budget.zero_dte_pct > 0.7 ? "text-amber-400" : "text-[#F8F8FF]/60"}>{zeroStr}{budget.zero_dte_pct > 0.7 ? " ⚠" : ""}</span>
                  {overBudget && budget.headroom_usd != null && (
                    <>
                      <span className="text-[#F8F8FF]/35">·</span>
                      <span className="font-bold text-red-400">OVER ${Math.abs(budget.headroom_usd).toFixed(0)}</span>
                    </>
                  )}
                  {!overBudget && budget.headroom_usd != null && (
                    <>
                      <span className="text-[#F8F8FF]/35">·</span>
                      <span className="text-[#39FF14]/60">room ${budget.headroom_usd.toFixed(0)}</span>
                    </>
                  )}
                </div>
              );
            })()}

            {/* ── "I'M IN THIS" trade entry strip ── */}
            <div className="mb-3 border border-[rgba(57,255,20,0.2)] p-2">
              <div className="mb-1.5 text-[9px] tracking-[0.3em] text-[#39FF14]/55">
                I'M IN THIS
              </div>

              {/* Symbol row */}
              <div className="mb-1.5 flex items-center gap-2">
                <input
                  className="w-20 shrink-0 border border-[rgba(57,255,20,0.25)] bg-black/40 px-2 py-1 font-mono uppercase text-[#F8F8FF] outline-none placeholder:text-[#F8F8FF]/25"
                  placeholder="SYMB"
                  value={tradeSymbol}
                  maxLength={10}
                  onChange={(e) => setTradeSymbol(e.target.value.toUpperCase())}
                />
                <label className="flex cursor-pointer items-center gap-1.5 text-[10px] text-[#F8F8FF]/55 select-none">
                  <input
                    type="checkbox"
                    checked={tradeOpen}
                    onChange={(e) => setTradeOpen(e.target.checked)}
                    className="accent-[#39FF14]"
                  />
                  Still open
                </label>
              </div>

              {/* Position line + MIC */}
              <div className="mb-1.5 flex gap-1">
                <textarea
                  className="min-h-[44px] flex-1 resize-none border border-[rgba(57,255,20,0.2)] bg-black/40 px-2 py-1 text-[#F8F8FF] outline-none placeholder:text-[#F8F8FF]/25"
                  placeholder={"e.g. STO 6× SPY 740p @1.05 · stopped −40%"}
                  rows={2}
                  value={tradeLine}
                  onChange={(e) => setTradeLine(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) void postDeskTrade();
                  }}
                />
                <button
                  type="button"
                  title="Dictate position line"
                  className={`shrink-0 self-start border px-2 py-1 text-[10px] transition-colors ${
                    micActive
                      ? "border-[#39FF14] text-[#39FF14] shadow-[0_0_8px_rgba(57,255,20,0.4)]"
                      : "border-[rgba(57,255,20,0.25)] text-[#F8F8FF]/50 hover:border-[#39FF14] hover:text-[#39FF14]"
                  }`}
                  onClick={toggleMic}
                >
                  {micActive ? "●" : "MIC"}
                </button>
              </div>

              {/* LOG TRADE */}
              <button
                type="button"
                disabled={tradeBusy || !tradeSymbol.trim() || !tradeLine.trim()}
                className="w-full border border-[rgba(57,255,20,0.45)] py-1 text-center text-[10px] tracking-widest text-[#39FF14] hover:bg-[rgba(57,255,20,0.08)] disabled:cursor-not-allowed disabled:opacity-35"
                onClick={() => void postDeskTrade()}
              >
                {tradeBusy ? "LOGGING…" : "LOG TRADE"}
              </button>

              {/* Toast — C: coach linkage hint */}
              {tradeToast && (
                <div className="mt-1.5 text-[9px] text-[#39FF14]/70">
                  Desk updated — coach will see this on next briefing refresh.
                </div>
              )}
            </div>

            {/* ── Desk timeline (trades + notes) ── */}
            <div className="mb-2 max-h-[200px] space-y-px overflow-y-auto">
              {deskTimeline.length === 0 ? (
                <div className="text-[#F8F8FF]/30">No desk entries yet.</div>
              ) : (
                deskTimeline.map((item) => {
                  const ts = item.ts?.slice(11, 16) ?? "";
                  const isTrade = item.kind === "trade";
                  return (
                    <div key={item.id} className="flex items-baseline gap-1.5 break-words leading-snug">
                      <span
                        className={`shrink-0 text-[9px] font-bold tracking-wide ${isTrade ? "text-[#39FF14]" : "text-[#F8F8FF]/40"}`}
                      >
                        {isTrade ? `TRADE` : "NOTE"}
                      </span>
                      {isTrade && item.symbol && (
                        <span className="shrink-0 text-[9px] text-[#39FF14]/70">{item.symbol}</span>
                      )}
                      <span className="flex-1 truncate text-[#F8F8FF]/65">
                        {isTrade ? (item.description ?? "") : (item.text ?? "")}
                      </span>
                      <span className="shrink-0 text-[9px] text-[#F8F8FF]/30">{ts}</span>
                    </div>
                  );
                })
              )}
            </div>

            {/* ── Ingest event feed (SSE) — upload + note events ── */}
            <div className="mb-2 max-h-[80px] space-y-0.5 overflow-y-auto border-t border-[rgba(57,255,20,0.06)] pt-1.5">
              {liveEvents.length === 0 ? (
                <div className="text-[#F8F8FF]/25">Waiting for feed…</div>
              ) : (
                [...liveEvents].reverse().map((e, i) => (
                  <div key={`${e.t}-${i}`} className="whitespace-pre-wrap break-words text-[#F8F8FF]/55">
                    {formatLiveLine(e)}
                  </div>
                ))
              )}
            </div>

            {/* ── Quick note ── */}
            <div className="flex gap-1">
              <input
                className="min-w-0 flex-1 border border-[rgba(57,255,20,0.2)] bg-black/40 px-2 py-1 text-[#F8F8FF] outline-none placeholder:text-[#F8F8FF]/25"
                placeholder="Quick note"
                value={deskNote}
                onChange={(e) => setDeskNote(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") void postDeskNote();
                }}
              />
              <button
                type="button"
                className="shrink-0 border border-[rgba(57,255,20,0.35)] px-2 py-1 text-[#39FF14] hover:bg-[rgba(57,255,20,0.08)]"
                onClick={() => void postDeskNote()}
              >
                NOTE
              </button>
            </div>

            {/* ── EOD upload ── */}
            <div className="mt-2 flex flex-wrap items-center gap-2 border-t border-[rgba(57,255,20,0.08)] pt-2">
              <label className="text-[#F8F8FF]/50">EOD CSV</label>
              <select
                className="border border-[rgba(57,255,20,0.2)] bg-black/40 px-1 py-0.5 text-[#F8F8FF]"
                value={uploadKind}
                onChange={(e) => setUploadKind(e.target.value as "tos_daily" | "options")}
              >
                <option value="tos_daily">TOS daily (SPY OHLCV)</option>
                <option value="options">Options chain (normalized)</option>
              </select>
              <label className="cursor-pointer border border-[rgba(57,255,20,0.35)] px-2 py-0.5 text-[#39FF14] hover:bg-[rgba(57,255,20,0.08)]">
                {uploadBusy ? "…" : "Choose file"}
                <input
                  type="file"
                  accept=".csv,text/csv"
                  className="hidden"
                  disabled={uploadBusy}
                  onChange={(e) => {
                    void onUploadCsv(e.target.files);
                    e.target.value = "";
                  }}
                />
              </label>
            </div>
          </div>

          {/* ── LLM / Strategy section ── */}
          <div className="min-h-0 flex-1 overflow-auto p-4 font-mono text-[12px] leading-relaxed text-[#F8F8FF]/90">
            <div className="mb-2 text-[10px] tracking-widest text-[#39FF14]/80">LLM · STRATEGY</div>
            <div className="prose prose-invert max-w-none prose-headings:text-[#39FF14] prose-a:text-[#39FF14]">
              <pre className="whitespace-pre-wrap font-mono text-[11px] text-[#F8F8FF]/85">
                {sidebar}
              </pre>
            </div>
          </div>
        </aside>
      </div>

      {paletteOpen && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center bg-black/70 pt-[18vh] backdrop-blur-sm"
          role="presentation"
          onMouseDown={() => setPaletteOpen(false)}
        >
          <div
            className="w-full max-w-lg rounded border border-[rgba(57,255,20,0.35)] p-4 shadow-[0_0_40px_rgba(57,255,20,0.12)]"
            style={{ background: "#080808" }}
            role="dialog"
            aria-modal="true"
            onMouseDown={(e) => e.stopPropagation()}
          >
            <div className="mb-2 font-mono text-[10px] tracking-[0.4em] text-[#39FF14]/80">
              COMMAND
            </div>
            <input
              autoFocus
              className="w-full border-b border-[rgba(57,255,20,0.25)] bg-transparent py-2 font-mono text-sm text-[#F8F8FF] outline-none placeholder:text-[#F8F8FF]/25"
              placeholder="Describe strategy test — Enter to execute"
              value={cmd}
              onChange={(e) => setCmd(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Escape") setPaletteOpen(false);
                if (e.key === "Enter" && cmd.trim()) {
                  void runBacktest(cmd.trim());
                  setCmd("");
                  setPaletteOpen(false);
                }
              }}
            />
            <div className="mt-3 flex justify-between font-mono text-[10px] text-[#F8F8FF]/35">
              <span>⌘K · Ctrl+K</span>
              <span style={{ color: ACCENT }}>ESC</span>
            </div>
          </div>
        </div>
      )}

      <footer
        className="border-t px-4 py-2 font-mono text-[10px] text-[#F8F8FF]/40"
        style={{ borderColor: "rgba(57,255,20,0.12)", background: PANEL }}
      >
        <button
          type="button"
          className="w-full text-left tracking-widest hover:text-[#39FF14]/80"
          onClick={() => setPaletteOpen(true)}
        >
          ⌘K COMMAND LINE — BACKTEST / LLM
        </button>
        {/* B — Nexus discipline hint */}
        <div className="mt-0.5 text-[#F8F8FF]/28 italic">
          Tools don't replace discipline — logging exposure lets coach/brain match reality.
        </div>
      </footer>
    </div>
  );
}
