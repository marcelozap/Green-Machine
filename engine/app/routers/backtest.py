from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.green_machine.backtester import GreenMachineBacktester
from app.llm import plan_backtest
from app.schemas import BacktestConfig, BacktestResult, LLMBacktestRequest
from app.services.similar_days import parse_vix_hint, similar_days_from_db
from app.services.vault import load_spy_daily

router = APIRouter(prefix="/backtest", tags=["backtest"])


async def _bars(session: AsyncSession, cfg: BacktestConfig):
    try:
        df = await load_spy_daily(session, start=cfg.start, end=cfg.end)
    except Exception:
        df = None
    if df is None or df.empty:
        return None
    df = df.copy()
    if "spy_return" not in df.columns and "close" in df.columns:
        df["spy_return"] = df["close"].pct_change().fillna(0.0)
    if "put_proxy_return" not in df.columns or df["put_proxy_return"].isna().all():
        if "spy_return" in df.columns:
            df["put_proxy_return"] = -df["spy_return"].clip(lower=-0.2, upper=0.2) * 1.15
        else:
            df["put_proxy_return"] = 0.0
    if "vix" not in df.columns:
        df["vix"] = 18.0
    else:
        df["vix"] = df["vix"].fillna(18.0)
    if "dte" not in df.columns:
        df["dte"] = 2
    return df


@router.post("/run", response_model=BacktestResult)
async def run_backtest(
    config: BacktestConfig,
    session: AsyncSession = Depends(get_session),
) -> BacktestResult:
    bt = GreenMachineBacktester(config=config)
    bars = await _bars(session, config)
    vix_hint = 20.0
    sim = await similar_days_from_db(session, vix_anchor=vix_hint, limit=6)
    res = bt.run(bars)
    return res.model_copy(update={"similar_days": sim, "config_resolved": config})


@router.post("/llm", response_model=BacktestResult)
async def run_from_llm(
    payload: LLMBacktestRequest,
    session: AsyncSession = Depends(get_session),
) -> BacktestResult:
    cfg, summary = await plan_backtest(payload.prompt)
    if payload.config is not None:
        cfg = payload.config
    bt = GreenMachineBacktester(config=cfg)
    bars = await _bars(session, cfg)
    vix_anchor = parse_vix_hint(payload.prompt)
    sim = await similar_days_from_db(session, vix_anchor=vix_anchor, limit=8)
    res = bt.run(bars)
    sim_note = ""
    if sim:
        sim_note = " Similar regimes: " + ", ".join(s.trade_date.isoformat() for s in sim[:5]) + "."
    return res.model_copy(
        update={
            "similar_days": sim,
            "llm_summary": summary + sim_note,
            "config_resolved": cfg,
        },
    )
