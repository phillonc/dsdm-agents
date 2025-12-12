"""
FastAPI REST API for OPTIX Backtester
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, List
from datetime import datetime
import structlog

from ..models.backtest import (
    BacktestConfig, BacktestResult, BacktestStatus,
    WalkForwardResult, MonteCarloResult
)
from ..engine.backtester import BacktestEngine
from ..optimization.walk_forward import WalkForwardOptimizer
from ..optimization.monte_carlo import MonteCarloSimulator
from ..data.market_data import SimulatedMarketDataProvider
from ..strategies.base import StrategyBase
from ...config.settings import settings

# Configure logging
logger = structlog.get_logger()

# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for results (would use database in production)
backtest_results: dict[str, BacktestResult] = {}
optimization_results: dict[str, WalkForwardResult] = {}
monte_carlo_results: dict[str, MonteCarloResult] = {}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "status": "operational"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/v1/backtest", response_model=BacktestResult)
async def create_backtest(
    config: BacktestConfig,
    background_tasks: BackgroundTasks
):
    """
    Create and run a new backtest
    
    Args:
        config: Backtest configuration
        background_tasks: FastAPI background tasks
        
    Returns:
        BacktestResult with initial status
    """
    try:
        # Create data provider (would use real data in production)
        data_provider = SimulatedMarketDataProvider(seed=42)
        
        # Create engine
        engine = BacktestEngine(data_provider, config)
        
        # For now, we'll run synchronously
        # In production, would run in background
        from ..strategies.example import SimpleStrategy
        strategy = SimpleStrategy()
        
        result = await engine.run(strategy)
        
        # Store result
        backtest_results[result.backtest_id] = result
        
        logger.info(
            "backtest_completed",
            backtest_id=result.backtest_id,
            total_trades=result.performance.total_trades
        )
        
        return result
        
    except Exception as e:
        logger.error("backtest_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/backtest/{backtest_id}", response_model=BacktestResult)
async def get_backtest(backtest_id: str):
    """
    Get backtest result by ID
    
    Args:
        backtest_id: Backtest ID
        
    Returns:
        BacktestResult
    """
    if backtest_id not in backtest_results:
        raise HTTPException(status_code=404, detail="Backtest not found")
    
    return backtest_results[backtest_id]


@app.get("/api/v1/backtests", response_model=List[dict])
async def list_backtests(
    status: Optional[BacktestStatus] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    List all backtests
    
    Args:
        status: Filter by status
        limit: Maximum number of results
        offset: Result offset
        
    Returns:
        List of backtest summaries
    """
    results = list(backtest_results.values())
    
    if status:
        results = [r for r in results if r.status == status]
    
    # Sort by start time
    results.sort(key=lambda x: x.start_time, reverse=True)
    
    # Paginate
    results = results[offset:offset + limit]
    
    # Return summaries
    summaries = [
        {
            "backtest_id": r.backtest_id,
            "status": r.status,
            "start_time": r.start_time,
            "total_trades": r.performance.total_trades,
            "total_return": r.performance.total_return,
            "sharpe_ratio": r.performance.sharpe_ratio
        }
        for r in results
    ]
    
    return summaries


@app.delete("/api/v1/backtest/{backtest_id}")
async def delete_backtest(backtest_id: str):
    """
    Delete a backtest
    
    Args:
        backtest_id: Backtest ID
        
    Returns:
        Success message
    """
    if backtest_id not in backtest_results:
        raise HTTPException(status_code=404, detail="Backtest not found")
    
    del backtest_results[backtest_id]
    
    return {"message": "Backtest deleted successfully"}


@app.post("/api/v1/backtest/{backtest_id}/monte-carlo", response_model=MonteCarloResult)
async def run_monte_carlo(
    backtest_id: str,
    iterations: int = 1000,
    method: str = "bootstrap"
):
    """
    Run Monte Carlo simulation on backtest results
    
    Args:
        backtest_id: Backtest ID
        iterations: Number of iterations
        method: Simulation method
        
    Returns:
        MonteCarloResult
    """
    if backtest_id not in backtest_results:
        raise HTTPException(status_code=404, detail="Backtest not found")
    
    base_result = backtest_results[backtest_id]
    
    try:
        simulator = MonteCarloSimulator(iterations=iterations)
        mc_result = simulator.simulate(base_result, method=method)
        
        # Store result
        monte_carlo_results[mc_result.simulation_id] = mc_result
        
        logger.info(
            "monte_carlo_completed",
            simulation_id=mc_result.simulation_id,
            iterations=iterations
        )
        
        return mc_result
        
    except Exception as e:
        logger.error("monte_carlo_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/optimize/walk-forward", response_model=WalkForwardResult)
async def run_walk_forward_optimization(
    config: BacktestConfig,
    param_grid: dict,
    num_periods: int = 5,
    train_ratio: float = 0.7
):
    """
    Run walk-forward optimization
    
    Args:
        config: Base backtest configuration
        param_grid: Parameter grid to search
        num_periods: Number of walk-forward periods
        train_ratio: Training/testing split ratio
        
    Returns:
        WalkForwardResult
    """
    try:
        # Create data provider
        data_provider = SimulatedMarketDataProvider(seed=42)
        
        # Create optimizer
        optimizer = WalkForwardOptimizer(
            data_provider,
            train_ratio=train_ratio,
            num_periods=num_periods
        )
        
        # Import strategy class
        from ..strategies.example import SimpleStrategy
        
        # Run optimization
        result = await optimizer.optimize(
            config,
            SimpleStrategy,
            param_grid
        )
        
        # Store result
        optimization_results[result.optimization_id] = result
        
        logger.info(
            "walk_forward_completed",
            optimization_id=result.optimization_id,
            num_periods=num_periods
        )
        
        return result
        
    except Exception as e:
        logger.error("walk_forward_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/optimize/{optimization_id}", response_model=WalkForwardResult)
async def get_optimization(optimization_id: str):
    """
    Get optimization result by ID
    
    Args:
        optimization_id: Optimization ID
        
    Returns:
        WalkForwardResult
    """
    if optimization_id not in optimization_results:
        raise HTTPException(status_code=404, detail="Optimization not found")
    
    return optimization_results[optimization_id]


@app.get("/api/v1/backtest/{backtest_id}/performance")
async def get_performance_metrics(backtest_id: str):
    """
    Get detailed performance metrics
    
    Args:
        backtest_id: Backtest ID
        
    Returns:
        Detailed performance metrics
    """
    if backtest_id not in backtest_results:
        raise HTTPException(status_code=404, detail="Backtest not found")
    
    result = backtest_results[backtest_id]
    
    return {
        "backtest_id": backtest_id,
        "performance": result.performance.dict(),
        "regime_performance": {
            regime: metrics.dict()
            for regime, metrics in result.regime_performance.items()
        },
        "summary": {
            "total_trades": result.performance.total_trades,
            "win_rate": result.performance.win_rate,
            "total_return": result.performance.total_return,
            "sharpe_ratio": result.performance.sharpe_ratio,
            "max_drawdown": result.performance.max_drawdown_percent,
            "profit_factor": result.performance.profit_factor
        }
    }


@app.get("/api/v1/backtest/{backtest_id}/trades")
async def get_trades(
    backtest_id: str,
    limit: int = 100,
    offset: int = 0
):
    """
    Get trades from backtest
    
    Args:
        backtest_id: Backtest ID
        limit: Maximum number of trades
        offset: Trade offset
        
    Returns:
        List of trades
    """
    if backtest_id not in backtest_results:
        raise HTTPException(status_code=404, detail="Backtest not found")
    
    result = backtest_results[backtest_id]
    trades = result.trades[offset:offset + limit]
    
    return {
        "backtest_id": backtest_id,
        "total_trades": len(result.trades),
        "trades": [t.dict() for t in trades]
    }


@app.get("/api/v1/backtest/{backtest_id}/equity-curve")
async def get_equity_curve(backtest_id: str):
    """
    Get equity curve data
    
    Args:
        backtest_id: Backtest ID
        
    Returns:
        Equity curve data
    """
    if backtest_id not in backtest_results:
        raise HTTPException(status_code=404, detail="Backtest not found")
    
    result = backtest_results[backtest_id]
    
    return {
        "backtest_id": backtest_id,
        "equity_curve": result.equity_curve
    }


@app.post("/api/v1/backtest/compare")
async def compare_backtests(backtest_ids: List[str]):
    """
    Compare multiple backtests
    
    Args:
        backtest_ids: List of backtest IDs to compare
        
    Returns:
        Comparison data
    """
    if not backtest_ids:
        raise HTTPException(status_code=400, detail="No backtest IDs provided")
    
    comparisons = []
    
    for backtest_id in backtest_ids:
        if backtest_id not in backtest_results:
            continue
        
        result = backtest_results[backtest_id]
        
        comparisons.append({
            "backtest_id": backtest_id,
            "config": {
                "start_date": result.config.start_date.isoformat(),
                "end_date": result.config.end_date.isoformat(),
                "initial_capital": result.config.initial_capital
            },
            "performance": {
                "total_trades": result.performance.total_trades,
                "win_rate": result.performance.win_rate,
                "total_return": result.performance.total_return,
                "sharpe_ratio": result.performance.sharpe_ratio,
                "sortino_ratio": result.performance.sortino_ratio,
                "max_drawdown": result.performance.max_drawdown_percent,
                "profit_factor": result.performance.profit_factor,
                "calmar_ratio": result.performance.calmar_ratio
            }
        })
    
    return {
        "comparison_count": len(comparisons),
        "backtests": comparisons
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error("unhandled_exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower()
    )
