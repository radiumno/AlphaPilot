"""ETF 分析器 — 跟踪误差、费率、流动性、折溢价、集中度"""

from typing import Optional
import pandas as pd
import numpy as np
from analysis.models.analysis import ETFAnalysisResult
from analysis.models.holdings import SectorExposure, HoldingDetail


def calc_tracking_error(etf_returns: pd.Series, index_returns: pd.Series) -> float:
    """计算年化跟踪误差(%) = std(etf_returns - index_returns) * sqrt(252)"""
    diff = etf_returns - index_returns
    if len(diff) < 2:
        return 0.0
    return round(float(diff.std() * np.sqrt(252)), 4)


def calc_concentration(weights: list[float]) -> float:
    """计算 HHI 集中度 = sum(weight^2)（weight 为百分比值）"""
    if not weights:
        return 0.0
    return round(sum(w ** 2 for w in weights), 2)


def analyze_etf(
    symbol: str,
    name: str,
    daily_data: Optional[pd.DataFrame] = None,
    index_data: Optional[pd.DataFrame] = None,
    holdings: Optional[list[dict]] = None,
    expense_ratio: float = 0.0,
    data_source: str = "",
) -> ETFAnalysisResult:
    """执行 ETF 分析。

    参数:
        symbol: ETF 代码
        name: ETF 名称
        daily_data: 日线数据（需含 close 列）
        index_data: 基准指数日线（需含 close 列）
        holdings: 持仓明细列表 [{"name":..., "weight":...}]
        expense_ratio: 管理费率(%)
        data_source: 数据来源名称
    """
    result = ETFAnalysisResult(
        symbol=symbol,
        name=name,
        expense_ratio=expense_ratio,
        data_source=data_source,
    )

    # 跟踪误差
    if daily_data is not None and index_data is not None:
        etf_close = daily_data["close"].dropna()
        idx_close = index_data["close"].dropna()
        common_idx = etf_close.index.intersection(idx_close.index)
        if len(common_idx) > 20:
            etf_ret = etf_close.loc[common_idx].pct_change().dropna()
            idx_ret = idx_close.loc[common_idx].pct_change().dropna()
            result.tracking_error = calc_tracking_error(etf_ret, idx_ret)

    # 波动率
    if daily_data is not None:
        close = daily_data["close"].dropna()
        if len(close) > 20:
            returns = close.pct_change().dropna()
            result.daily_volume = float(daily_data.get("volume", pd.Series([0])).mean())
            result.nav_price = float(close.iloc[-1])

    # 行业和持仓
    if holdings:
        result.holdings = [
            HoldingDetail(name=h["name"], symbol=h.get("symbol", ""), weight=h["weight"])
            for h in holdings if h.get("weight", 0) > 0
        ]
        weights = [h["weight"] for h in holdings if h.get("weight", 0) > 0]
        result.concentration = calc_concentration(weights)

    return result
