from fastapi import APIRouter

from app.green_machine.backtester import GreenMachineBacktester
from app.schemas import BacktestConfig, BacktestResult, LLMBacktestRequest

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.post("/run", response_model=BacktestResult)
async def run_backtest(config: BacktestConfig) -> BacktestResult:
    bt = GreenMachineBacktester(config=config)
    return bt.run()


@router.post("/llm", response_model=BacktestResult)
async def run_from_llm(payload: LLMBacktestRequest) -> BacktestResult:
    """
    Command-bar entrypoint. LLM service maps natural language → BacktestConfig
    and optional condition function (future: validated sandbox exec).
    """
    cfg = payload.config or BacktestConfig()
    bt = GreenMachineBacktester(config=cfg)
    return bt.run()
