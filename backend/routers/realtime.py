import logging, re, json, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from fastapi import APIRouter, Query
from db import list_holdings, list_watch

logger = logging.getLogger(__name__)
router = APIRouter()

def _fetch_one(code):
    try:
        url = f"http://fundgz.1234567.com.cn/js/{code}.js"
        req = urllib.request.Request(url, headers={
            "Referer":"http://fund.eastmoney.com/",
            "User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=5) as resp:
            text = resp.read().decode("utf-8","replace")
        m = re.search(r'jsonpgz\((.*)\)', text)
        if m:
            data = json.loads(m.group(1))
            return {"code":data.get("fundcode",code),"name":data.get("name",""),
                    "nav":data.get("dwjz",""),"estimated_nav":data.get("gsz",""),
                    "estimated_change":data.get("gszzl",""),"update_time":data.get("gztime","")}
    except: pass
    return {"code":code,"name":"","error":"获取失败"}

def _is_trading():
    now = datetime.now()
    return now.weekday()<5 and ((now.hour>9 or (now.hour==9 and now.minute>=30)) and now.hour<15)

@router.get("/")
def realtime_valuation(filter: str = Query("all")):
    holdings = list_holdings()
    watchlist = list_watch()
    fund_set = {}
    for h in holdings:
        c = h["code"]; fund_set.setdefault(c,{"tags":[]})["tags"].append("持有")
    for w in watchlist:
        c = w["code"]; fund_set.setdefault(c,{"tags":[]})["tags"].append("自选")
    if filter=="holding": fund_set = {k:v for k,v in fund_set.items() if "持有" in v["tags"]}
    elif filter=="watch": fund_set = {k:v for k,v in fund_set.items() if "自选" in v["tags"]}
    codes = list(fund_set.keys())
    if not codes:
        return {"funds":[],"update_time":datetime.now().strftime("%H:%M:%S"),"is_trading":_is_trading()}
    results = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(_fetch_one,c):c for c in codes}
        for f in as_completed(futures):
            try:
                r = f.result()
                if r: r["tags"] = fund_set.get(r["code"],{}).get("tags",[])
                results.append(r)
            except: pass
    results.sort(key=lambda r: float(r.get("estimated_change",0) or 0), reverse=True)
    return {"funds":results,"update_time":datetime.now().strftime("%H:%M:%S"),"is_trading":_is_trading()}
