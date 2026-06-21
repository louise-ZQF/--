import numpy as np, pandas as pd
from services.data import get_nav

def dca_backtest(code, amount=1000, freq="W"):
    df = get_nav(code)
    if df.empty:
        return {"error": "无净值数据"}
    nav = df.set_index("date")["nav"]
    buy_dates = nav.resample(freq).first().dropna().index
    shares = cost = 0.0
    curve = []
    for d in nav.index:
        if d in buy_dates:
            price = nav.loc[d]
            shares += amount / price
            cost += amount
        value = shares * nav.loc[d]
        curve.append({"date": d.strftime("%Y-%m-%d"), "value": round(value,2), "cost": round(cost,2)})
    if not curve:
        return {"error": "无足够数据"}
    final = curve[-1]["value"]
    total_ret = final / cost - 1 if cost else 0
    days = (nav.index[-1] - nav.index[0]).days or 1
    ann = (1 + total_ret) ** (365 / days) - 1
    s = pd.Series([c["value"] for c in curve])
    mdd = float((s / s.cummax() - 1).min())
    return {
        "curve": curve[::max(1, len(curve)//100)],
        "total_invested": round(cost,2),
        "final_value": round(final,2),
        "total_return": round(total_ret,4),
        "annualized": round(ann,4),
        "max_drawdown": round(mdd,4),
    }
