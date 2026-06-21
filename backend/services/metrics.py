"""绩效指标计算"""
import numpy as np
import pandas as pd

def max_drawdown(nav: pd.Series) -> float:
    """最大回撤。"""
    cummax = nav.cummax()
    return float((nav / cummax - 1).min())

def nav_percentile(nav: pd.Series, window_years: int = 3) -> float:
    """当前净值在近N年中的分位(越低越便宜)。"""
    s = nav.tail(252 * window_years)
    if len(s) < 20:
        return 0.5
    cur = s.iloc[-1]
    return float((s < cur).mean())

def trend_ma(nav: pd.Series, win: int = 60) -> str:
    """60日均线方向。"""
    ma = nav.rolling(win).mean()
    if len(ma.dropna()) < 5:
        return "未知"
    return "向上" if ma.iloc[-1] > ma.iloc[-5] else "向下"

def annual_return(nav: pd.Series) -> float:
    """年化收益率。"""
    if len(nav) < 2:
        return 0.0
    total = nav.iloc[-1] / nav.iloc[0] - 1
    try:
        days = (nav.index[-1] - nav.index[0]).days
    except AttributeError:
        days = len(nav) - 1
    days = days or 1
    if total <= -1:
        return -1.0
    return float((1 + total) ** (365 / days) - 1)

def annual_volatility(rets: pd.Series) -> float:
    """年化波动率。"""
    return float(rets.std() * np.sqrt(252)) if len(rets) > 1 else 0.0

def sharpe_ratio(rets: pd.Series, rf: float = 0.02) -> float:
    """夏普比率。"""
    ann_ret = annual_return(rets)
    ann_vol = annual_volatility(rets)
    return float((ann_ret - rf) / (ann_vol + 1e-9)) if ann_vol > 0 else 0.0

def rsi(nav: pd.Series, n: int = 14) -> float:
    """RSI 指标。"""
    diff = nav.diff()
    up = diff.clip(lower=0).rolling(n).mean()
    down = (-diff.clip(upper=0)).rolling(n).mean()
    rs = up / (down + 1e-9)
    return float(100 - 100 / (1 + rs.iloc[-1])) if not rs.empty else 50.0

def sortino_ratio(rets: pd.Series, rf: float = 0.02) -> float:
    """索提诺比率(只计下行风险)。"""
    downside = rets[rets < 0]
    if len(downside) < 2:
        return 0.0
    ann_ret = annual_return(rets)
    ann_down_vol = downside.std() * np.sqrt(252)
    return float((ann_ret - rf) / (ann_down_vol + 1e-9)) if ann_down_vol > 0 else 0.0

def calmar_ratio(nav: pd.Series, rf: float = 0.02) -> float:
    """Calmar比率 = (年化收益率-无风险利率) / 最大回撤绝对值。"""
    ann_ret = annual_return(nav)
    mdd = max_drawdown(nav)
    if mdd >= 0:
        return 0.0
    return float((ann_ret - rf) / (abs(mdd) + 1e-9))
