"""相关性分析器 — 相关系数矩阵、滚动相关性、聚类"""

from typing import Optional
import pandas as pd
import numpy as np
from analysis.models.correlation import CorrelationPair, CorrelationMatrix


def calc_correlation_matrix(nav_dict: dict[str, pd.Series]) -> CorrelationMatrix:
    """计算多资产收益率相关系数矩阵

    参数:
        nav_dict: {symbol: nav_series}
    """
    symbols = list(nav_dict.keys())
    if len(symbols) < 2:
        return CorrelationMatrix(symbols=symbols)

    # 统一收益率序列
    returns_df = None
    for symbol, nav in nav_dict.items():
        if len(nav) < 10:
            continue
        r = nav.pct_change().dropna()
        if returns_df is None:
            returns_df = pd.DataFrame({symbol: r})
        else:
            returns_df[symbol] = r

    if returns_df is None or len(returns_df.columns) < 2:
        return CorrelationMatrix(symbols=list(returns_df.columns) if returns_df is not None else symbols)

    returns_df = returns_df.dropna()
    valid_symbols = list(returns_df.columns)
    n = len(valid_symbols)

    corr_matrix_df = returns_df.corr()
    matrix = [[round(float(corr_matrix_df.iloc[i, j]), 4) for j in range(n)] for i in range(n)]

    # 两两配对
    pairs: list[CorrelationPair] = []
    for i in range(n):
        for j in range(i + 1, n):
            corr_val = corr_matrix_df.iloc[i, j]
            if pd.isna(corr_val):
                corr_val = 0.0
            rolling = _calc_rolling_correlation(returns_df[valid_symbols[i]], returns_df[valid_symbols[j]])
            pairs.append(CorrelationPair(
                symbol_a=valid_symbols[i],
                symbol_b=valid_symbols[j],
                correlation=round(float(corr_val), 4),
                rolling_correlation=rolling,
            ))

    avg_corr = float(np.mean([p.correlation for p in pairs])) if pairs else 0.0

    # 简单阈值聚类 (corr > 0.7 为一组)
    cluster_info = _cluster_by_correlation(valid_symbols, corr_matrix_df)

    return CorrelationMatrix(
        symbols=valid_symbols,
        matrix=matrix,
        pairs=pairs,
        avg_correlation=round(avg_corr, 4),
        cluster_info=cluster_info,
    )


def _calc_rolling_correlation(s1: pd.Series, s2: pd.Series, window: int = 60) -> Optional[float]:
    """计算滚动相关系数（最近 window 期）"""
    if len(s1) < window or len(s2) < window:
        return None
    r1 = s1.iloc[-window:]
    r2 = s2.iloc[-window:]
    if r1.std() == 0 or r2.std() == 0:
        return None
    return round(float(r1.corr(r2)), 4)


def _cluster_by_correlation(
    symbols: list[str], corr_df: pd.DataFrame, threshold: float = 0.7
) -> dict[str, list[str]]:
    """基于相关性阈值简单聚类"""
    assigned = set()
    clusters: dict[str, list[str]] = {}
    cluster_id = 0

    for i, s1 in enumerate(symbols):
        if s1 in assigned:
            continue
        # 创建新簇
        cluster_name = f"cluster_{cluster_id}"
        clusters[cluster_name] = [s1]
        assigned.add(s1)

        for s2 in symbols[i + 1:]:
            if s2 in assigned:
                continue
            if s1 in corr_df.index and s2 in corr_df.columns:
                if abs(corr_df.loc[s1, s2]) > threshold:
                    clusters[cluster_name].append(s2)
                    assigned.add(s2)
        cluster_id += 1

    # 单元素簇不返回
    return {k: v for k, v in clusters.items() if len(v) > 1}
