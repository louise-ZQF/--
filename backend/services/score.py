import pandas as pd
from services.data import get_rank, get_nav
from services.metrics import max_drawdown, nav_percentile

def screen_4433():
    df = get_rank()
    if df.empty:
        return []
    cols = {"近1年":"y1","近2年":"y2","近3年":"y3","今年来":"ytd","近6月":"m6","近3月":"m3"}
    for raw, key in cols.items():
        if raw in df.columns:
            df[key] = pd.to_numeric(df[raw], errors="coerce")
    def top(series, frac):
        return series >= series.quantile(1 - frac)
    try:
        mask = (top(df["y1"],0.25) & top(df["y2"],0.25) & top(df["y3"],0.25) &
                top(df["ytd"],0.25) & top(df["m6"],1/3) & top(df["m3"],1/3))
        keep = ["基金代码","基金简称","y1","y2","y3","m6","m3"]
        keep = [c for c in keep if c in df.columns]
        return df[mask][keep].head(50).to_dict(orient="records")
    except Exception:
        return []

def score_fund(code: str) -> dict:
    df = get_nav(code)
    if df.empty:
        return {"code": code, "error": "无净值数据"}
    nav = df["nav"]
    pct = nav_percentile(nav)
    mdd = max_drawdown(nav.tail(252))
    s_elastic = round((1 - pct) * 20, 1)
    s_dd = round(max(0, (1 + mdd / 0.5)) * 15, 1)
    total = round(40 + s_elastic + s_dd, 1)
    rating = "契合" if total >= 70 else ("中性" if total >= 50 else "不契合")
    return {"code":code,"score":total,"rating":rating,
            "detail":{"低位弹性":s_elastic,"回撤控制":s_dd,"净值分位":round(pct,2),"最大回撤":round(mdd,2)}}
