"""风险分析数据模型 — VaR、CVaR、回撤、波动率"""

from typing import Optional
from pydantic import BaseModel, Field


class VaRResult(BaseModel):
    """VaR/CVaR 计算结果"""
    parametric_95: float = Field(default=0.0, description="参数法 VaR 95% (%)")
    parametric_99: float = Field(default=0.0, description="参数法 VaR 99% (%)")
    historical_95: float = Field(default=0.0, description="历史法 VaR 95% (%)")
    historical_99: float = Field(default=0.0, description="历史法 VaR 99% (%)")
    cvar_95: float = Field(default=0.0, description="CVaR 95% (%)")
    cvar_99: float = Field(default=0.0, description="CVaR 99% (%)")


class DrawdownInfo(BaseModel):
    """回撤分析信息"""
    max_drawdown: float = Field(default=0.0, description="最大回撤(%)")
    current_drawdown: float = Field(default=0.0, description="当前回撤(%)")
    avg_drawdown: float = Field(default=0.0, description="平均回撤(%)")
    drawdown_days: int = Field(default=0, description="处于回撤期的天数")
    recovery_days: int = Field(default=0, description="从最大回撤恢复所需天数")


class RiskMetrics(BaseModel):
    """单一资产风险指标"""
    symbol: str
    name: str
    volatility: float = Field(default=0.0, description="年化波动率(%)")
    downside_volatility: float = Field(default=0.0, description="下行波动率(%)")
    sortino_ratio: Optional[float] = Field(default=None, description="Sortino 比率(下行风险调整收益)")
    calmar_ratio: Optional[float] = Field(default=None, description="Calmar 比率(收益/最大回撤)")
    information_ratio: Optional[float] = Field(default=None, description="Information 比率(超额收益/跟踪误差)")
    var: VaRResult = Field(default_factory=VaRResult)
    drawdown: DrawdownInfo = Field(default_factory=DrawdownInfo)
    beta: Optional[float] = Field(default=None, description="Beta 系数")
    alpha: Optional[float] = Field(default=None, description="Alpha 系数(%)")
    annualized_return: Optional[float] = Field(default=None, description="年化收益率(%)")
    data_source: str = ""


class PortfolioRiskResult(BaseModel):
    """组合级风险分析结果"""
    portfolio_volatility: float = Field(default=0.0, description="组合年化波动率(%)")
    portfolio_var: VaRResult = Field(default_factory=VaRResult)
    diversification_ratio: float = Field(default=0.0, description="分散化比率(加权平均波动/组合波动)")
    asset_risks: list[RiskMetrics] = Field(default_factory=list)
