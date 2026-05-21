"""主动基金分析器 — 业绩指标、风格分析"""

from typing import Optional
import pandas as pd
import numpy as np
from analysis.models.analysis import FundAnalysisResult


def calc_sharpe_ratio(returns: pd.Series, risk_free: float = 0.03) -> float:
    """计算年化夏普比率"""
    if len(returns) < 10:
        return 0.0
    excess = returns - risk_free / 252
    if excess.std() == 0:
        return 0.0
    return round(float(excess.mean() / excess.std() * np.sqrt(252)), 4)


def calc_max_drawdown(nav: pd.Series) -> float:
    """计算最大回撤(%)"""
    if len(nav) < 2:
        return 0.0
    rolling_max = nav.expanding().max()
    drawdowns = (nav - rolling_max) / rolling_max
    mdd = abs(float(drawdowns.min()))
    return round(mdd * 100, 2)


def analyze_fund(
    symbol: str,
    name: str,
    nav_data: Optional[pd.Series] = None,
    info: Optional[dict] = None,
    holdings: Optional[list[dict]] = None,
    data_source: str = "",
) -> FundAnalysisResult:
    """执行主动基金分析。

    参数:
        symbol: 基金代码
        name: 基金名称
        nav_data: 净值时间序列
        info: 基金基本信息字典
        holdings: 持仓明细
        data_source: 数据来源
    """
    result = FundAnalysisResult(
        symbol=symbol,
        name=name,
        data_source=data_source,
    )

    if info:
        result.manager_name = info.get("manager", "")
        result.style_label = info.get("style", info.get("category", ""))

    if nav_data is not None and len(nav_data) > 20:
        returns = nav_data.pct_change().dropna()
        result.sharpe_ratio = calc_sharpe_ratio(returns)
        result.max_drawdown_1y = calc_max_drawdown(nav_data)

        # 计算不同周期的收益率
        result.nav_return_1y = _calc_period_return(nav_data, 252)
        result.nav_return_3y = _calc_period_return(nav_data, 756)

    return result


def _calc_period_return(nav: pd.Series, trading_days: int) -> float:
    """计算指定交易日数的收益率(%)"""
    if len(nav) < trading_days:
        return 0.0
    start = nav.iloc[-trading_days - 1]
    end = nav.iloc[-1]
    if start == 0:
        return 0.0
    return round(float((end - start) / start * 100), 2)
