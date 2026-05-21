"""agents 包 — 向后兼容，从新路径 re-export"""

from analysis.analyzers.etf_analyzer import analyze_etf, calc_tracking_error, calc_concentration
from analysis.analyzers.fund_analyzer import analyze_fund, calc_sharpe_ratio, calc_max_drawdown
from analysis.analyzers.risk_analyzer import (
    analyze_risk_single, analyze_portfolio_risk,
    calc_var_parametric, calc_var_historical, calc_cvar,
    calc_downside_volatility, analyze_drawdown,
)
from analysis.analyzers.correlation import calc_correlation_matrix
from analysis.analyzers.concentration import (
    calc_portfolio_hhi, calc_effective_n, calc_top_n_concentration,
    calc_sector_concentration, detect_concentration_risks,
)
from analysis.analyzers.stress_test import run_stress_test
from analysis.analyzers.optimization import (
    optimize_max_sharpe, optimize_min_volatility, risk_parity_weights,
    compute_efficient_frontier, compute_current_portfolio,
    full_portfolio_optimization,
    OptimizationResult, PortfolioOptimizationResult, EfficientFrontierPoint,
)
from analysis.debate.debate import run_debate

__all__ = [
    "analyze_etf", "calc_tracking_error", "calc_concentration",
    "analyze_fund", "calc_sharpe_ratio", "calc_max_drawdown",
    "analyze_risk_single", "analyze_portfolio_risk",
    "calc_var_parametric", "calc_var_historical", "calc_cvar",
    "calc_downside_volatility", "analyze_drawdown",
    "calc_correlation_matrix",
    "calc_portfolio_hhi", "calc_effective_n", "calc_top_n_concentration",
    "calc_sector_concentration", "detect_concentration_risks",
    "run_stress_test",
    "optimize_max_sharpe", "optimize_min_volatility", "risk_parity_weights",
    "compute_efficient_frontier", "compute_current_portfolio",
    "full_portfolio_optimization",
    "OptimizationResult", "PortfolioOptimizationResult", "EfficientFrontierPoint",
    "run_debate",
]
