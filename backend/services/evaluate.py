"""Unified fund evaluation engine — single source of truth for all pages."""
import logging
from datetime import datetime
import pandas as pd
from cache import cached
from services.data import get_nav, get_short_term_perf, get_fund_manager_info, get_rank
from services.metrics import nav_percentile, max_drawdown, annual_volatility, sharpe_ratio

logger = logging.getLogger(__name__)


def evaluate_fund(code: str, fund_name: str = "") -> dict:
    try:
        df = get_nav(code)
    except Exception:
        df = None
    if df is None or df.empty:
        return _empty("无净值数据")

    nav = df["nav"]
    val = _score_valuation(nav, code)
    qual = _score_quality(code, fund_name, nav)
    mom = _score_momentum(code)
    risk = _score_risk(nav)

    total = round(val * 0.30 + qual * 0.35 + mom * 0.20 + risk * 0.15, 1)
    vl = _val_label(val)
    ql = _qual_label(qual)
    action, detail = _decide(vl, ql)

    return {
        "total_score": total,
        "valuation_score": round(val, 1), "quality_score": round(qual, 1),
        "momentum_score": round(mom, 1), "risk_score": round(risk, 1),
        "valuation_label": vl, "quality_label": ql,
        "action": action, "action_detail": detail,
        "summary": f"{ql}·{vl} — {action}",
    }

def _empty(reason): return {"total_score":0,"valuation_score":0,"quality_score":0,"momentum_score":0,"risk_score":0,"valuation_label":"未知","quality_label":"未知","action":"数据不足","action_detail":reason,"summary":"数据不足"}
def _val_label(s): return "便宜" if s>75 else ("合理" if s>=50 else "偏贵")
def _qual_label(s): return "优质" if s>70 else ("一般" if s>=40 else "较差")

_D = {
    ("便宜","优质"):("强烈买入","估值偏低且质量优秀，当前是较好买入时机，建议分批建仓"),
    ("便宜","一般"):("可买入","估值偏低但质量一般，建议小仓试探或选同类更优标的"),
    ("便宜","较差"):("谨慎","估值虽低但质量较差，需谨慎评估"),
    ("合理","优质"):("继续持有","质量优秀且估值合理，建议继续持有"),
    ("合理","一般"):("观望","估值合理但质量一般，建议观望等更好时机"),
    ("合理","较差"):("不建议","质量较差且估值无优势，不建议当前介入"),
    ("偏贵","优质"):("逢回调加仓","质量优秀但当前估值偏高，建议等5-10%回调后分批建仓"),
    ("偏贵","一般"):("减仓","估值偏高且质量一般，建议减仓控制风险"),
    ("偏贵","较差"):("强烈减仓","估值偏高且质量较差，建议立即减仓"),
}
def _decide(vl,ql): return _D.get((vl,ql),("观望","数据不足以明确判断"))

# --- dimension scorers ---

def _score_valuation(nav, code):
    try: pct = nav_percentile(nav)
    except: pct = 0.5
    ps = (1.0-pct)*100.0
    try:
        perf = get_short_term_perf(code)
        rp = perf.get("rank_pct")
        peer = max(0,(1.0-rp/100)*100) if (rp is not None and rp>0) else 50
    except: peer = 50
    return ps*0.5 + peer*0.5

def _score_quality(code, name, nav):
    s4433 = _check_4433(code)
    if nav is not None and len(nav)>=20:
        try:
            rets = nav.pct_change().dropna()
            s = sharpe_ratio(rets) if len(rets)>=20 else 0
            ssharpe = min(100,s/3*100) if s>0 else 0
        except: ssharpe = 0
        try:
            mdd = max_drawdown(nav.tail(252))
            sdd = max(0, min(100, (1+mdd/0.4)*100))
        except: sdd = 0
    else: ssharpe = sdd = 0
    try:
        mgr = get_fund_manager_info(code)
        d = mgr.get("appointment_date","")
        if d:
            try:
                yrs = (datetime.now()-datetime.strptime(d,"%Y-%m-%d")).days/365
                stenure = 100 if yrs>=5 else (60 if yrs>=2 else 30)
            except: stenure = 30
        else: stenure = 30
    except: stenure = 30
    return s4433*0.40 + ssharpe*0.25 + sdd*0.20 + stenure*0.15

def _score_momentum(code):
    try:
        rp = get_short_term_perf(code).get("rank_pct")
        if rp is not None and rp>0:
            return 100 if rp<20 else (75 if rp<40 else (50 if rp<60 else (25 if rp<80 else 10)))
    except: pass
    return 50

def _score_risk(nav):
    try:
        rets = nav.pct_change().dropna()
        vol = annual_volatility(rets) if len(rets)>=5 else 0.2
        vs = max(0,min(100,(1-vol/0.4)*100))
    except: vs = 50
    try:
        mdd = max_drawdown(nav.tail(252))
        ms = max(0,min(100,(1+mdd/0.4)*100))
    except: ms = 50
    return vs*0.5 + ms*0.5

@cached(ttl=86400)
def _check_4433(code):
    try:
        df = get_rank()
        if df.empty: return 0
        cm = {"近1年":"y1","近2年":"y2","近3年":"y3","今年来":"ytd","近6月":"m6","近3月":"m3"}
        for r,k in cm.items():
            if r in df.columns: df[k]=pd.to_numeric(df[r],errors="coerce")
        def t(s,f): return s>=s.quantile(1-f)
        mask = t(df["y1"],.25)&t(df["y2"],.25)&t(df["y3"],.25)&t(df["ytd"],.25)&t(df["m6"],1/3)&t(df["m3"],1/3)
        return 100 if str(code) in df.loc[mask,"基金代码"].astype(str).values else 0
    except: return 0
