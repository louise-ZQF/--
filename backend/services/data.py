"""akshare 数据封装 + 统一缓存"""
import akshare as ak
import pandas as pd
from cache import cached

@cached(ttl=3600)
def get_nav(code: str) -> pd.DataFrame:
    """获取基金单位净值走势。"""
    try:
        df = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
        cols = ["date","nav","acc_nav","growth"][:len(df.columns)]
        df.columns = cols
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
        return df.dropna(subset=["nav"])
    except Exception:
        return pd.DataFrame(columns=["date","nav"])

@cached(ttl=86400)
def get_rank() -> pd.DataFrame:
    """基金业绩排行。"""
    try:
        return ak.fund_open_fund_rank_em(symbol="全部")
    except Exception:
        return pd.DataFrame()

@cached(ttl=86400)
def get_all_funds() -> pd.DataFrame:
    """全市场基金列表。"""
    try:
        return ak.fund_name_em()
    except Exception:
        return pd.DataFrame()

@cached(ttl=86400)
def get_fund_info(code: str) -> dict:
    """基金基本信息(雪球)。"""
    try:
        return ak.fund_individual_basic_info_xq(symbol=code)
    except Exception:
        return {}

@cached(ttl=86400)
def get_manager() -> pd.DataFrame:
    """基金经理信息。"""
    try:
        return ak.fund_manager_em()
    except Exception:
        return pd.DataFrame()

@cached(ttl=86400)
def get_index_daily(code: str) -> pd.DataFrame:
    """指数日线。code='sh000300'=沪深300"""
    try:
        return ak.stock_zh_index_daily(symbol=code)
    except Exception:
        return pd.DataFrame()
