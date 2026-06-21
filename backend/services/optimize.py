import numpy as np, pandas as pd
from scipy.optimize import minimize
from services.data import get_nav

def _returns_matrix(codes):
    navs = {}
    for c in codes:
        df = get_nav(c)
        if not df.empty:
            navs[c] = df.set_index("date")["nav"]
    if not navs:
        return pd.DataFrame()
    px = pd.DataFrame(navs).dropna()
    return px.pct_change().dropna()

def optimize(codes, method="max_sharpe", rf=0.02):
    rets = _returns_matrix(codes)
    if rets.empty or len(rets.columns) < 2:
        return {"error": "数据不足,至少需要2只有效净值的基金", "weights": {}}
    mu = rets.mean() * 252
    cov = rets.cov() * 252
    n = len(codes)
    w0 = np.ones(n) / n
    bounds = [(0, 1)] * n
    cons = [{"type": "eq", "fun": lambda w: w.sum() - 1}]

    if method == "min_var":
        obj = lambda w: w @ cov.values @ w
    elif method == "risk_parity":
        def obj(w):
            port_var = w @ cov.values @ w
            mrc = cov.values @ w
            rc = w * mrc
            target = port_var / n
            return ((rc - target) ** 2).sum()
    else:
        def obj(w):
            ret = w @ mu.values
            vol = np.sqrt(w @ cov.values @ w)
            return -(ret - rf) / (vol + 1e-9)

    res = minimize(obj, w0, method="SLSQP", bounds=bounds, constraints=cons)
    w = res.x / res.x.sum()
    port_ret = float(w @ mu.values)
    port_vol = float(np.sqrt(w @ cov.values @ w))
    return {
        "weights": {c: round(float(wi), 4) for c, wi in zip(codes, w)},
        "expected_return": round(port_ret, 4),
        "expected_vol": round(port_vol, 4),
        "sharpe": round((port_ret - rf) / (port_vol + 1e-9), 3),
    }
