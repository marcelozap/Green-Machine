import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ColorType,
  createChart,
  CrosshairMode,
  type IChartApi,
  type ISeriesApi,
  LineStyle,
} from "lightweight-charts";

type EquityPoint = [string, number];

type BacktestResponse = {
  equity_curve: EquityPoint[];
  sharpe: number | null;
  sortino: number | null;
  calmar: number | null;
  max_drawdown: number;
  total_return: number;
  circuit_breaker_hit: boolean;
  notes: string;
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
    const series = chart.addAreaSeries({
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
  const [snapshot, setSnapshot] = useState({ spy: "—", vix: "—" });
  const [pulse, setPulse] = useState(true);
  const [equity, setEquity] = useState<EquityPoint[]>([]);
  const [stats, setStats] = useState<BacktestResponse | null>(null);
  const [sidebar, setSidebar] = useState(
    "## Strategy terminal\n\nAwaiting command. Use **⌘K** / **Ctrl+K** to run a backtest.\n",
  );
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [cmd, setCmd] = useState("");

  const runBacktest = useCallback(async (prompt: string) => {
    setSidebar((s) => s + `\n> ${prompt}\n`);
    const res = await fetch("/backtest/llm", {
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
    setSidebar(
      (s) =>
        s +
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
        const h = await fetch("/health");
        if (!h.ok) return;
        const m = await fetch("/market/snapshot");
        if (!m.ok) return;
        const j = (await m.json()) as { spy: number; vix: number };
        setSnapshot({ spy: j.spy.toFixed(2), vix: j.vix.toFixed(2) });
      } catch {
        /* cockpit still usable offline */
      }
    })();
  }, []);

  const metrics = useMemo(() => {
    if (!stats) return "—";
    return [
      `Sharpe ${stats.sharpe?.toFixed(2) ?? "n/a"}`,
      `Sortino ${stats.sortino?.toFixed(2) ?? "n/a"}`,
      `Calmar ${stats.calmar?.toFixed(2) ?? "n/a"}`,
    ].join("  ·  ");
  }, [stats]);

  return (
    <div className="flex min-h-screen flex-col">
      <header
        className="flex items-center justify-between border-b px-6 py-3"
        style={{ borderColor: "rgba(57,255,20,0.15)", background: PANEL }}
      >
        <div className="font-mono text-xs tracking-[0.35em] text-[#39FF14]">GREEN MACHINE</div>
        <div className="flex gap-8 font-mono text-sm text-[#F8F8FF]">
          <span>
            SPY <span className="text-[#39FF14]">{snapshot.spy}</span>
          </span>
          <span>
            VIX <span className="text-[#39FF14]">{snapshot.vix}</span>
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

      <div className="grid flex-1 grid-cols-1 gap-0 lg:grid-cols-[1fr_280px]">
        <main className="flex flex-col border-r border-[rgba(57,255,20,0.08)]">
          <div className="border-b border-[rgba(57,255,20,0.08)] px-4 py-2 font-mono text-[11px] text-[#F8F8FF]/70">
            CUMULATIVE PnL · {metrics}
          </div>
          <div className="flex-1 p-2">
            <ChartPane data={equity} />
          </div>
        </main>

        <aside
          className="max-h-[40vh] overflow-auto border-t border-[rgba(57,255,20,0.08)] p-4 font-mono text-[12px] leading-relaxed text-[#F8F8FF]/90 lg:max-h-none lg:border-t-0"
          style={{ background: PANEL }}
        >
          <div className="mb-2 text-[10px] tracking-widest text-[#39FF14]/80">LLM · STRATEGY</div>
          <div className="prose prose-invert max-w-none prose-headings:text-[#39FF14] prose-a:text-[#39FF14]">
            {/* lightweight markdown-ish: we render pre-wrapped content */}
            <pre className="whitespace-pre-wrap font-mono text-[11px] text-[#F8F8FF]/85">
              {sidebar}
            </pre>
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
      </footer>
    </div>
  );
}
