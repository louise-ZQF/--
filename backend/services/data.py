"""akshare 数据封装 + 统一缓存 + 天天基金 HTML 抓取 (FundCrawler 模式)"""
import re
import urllib.request
import json
from typing import Optional
import akshare as ak
import pandas as pd
from cache import cached

# ── 天天基金 HTML 抓取工具 (FundCrawler 模式) ──────────────────

_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
_REFERER = "http://fund.eastmoney.com/"
_NUMBER_RE = r'-?(\d+?(,\d+)*?(\.\d+)?)'


def _fetch_html(url: str, timeout: int = 8) -> Optional[str]:
    """抓取 HTML 页面，失败返回 None。"""
    try:
        req = urllib.request.Request(url, headers={
            "Referer": _REFERER, "User-Agent": _USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None


@cached(ttl=86400)
def get_fund_direction(code: str) -> list:
    """获取基金投资方向（基于持仓关键词）。"""
    try:
        holdings = ak.fund_portfolio_hold_em(symbol=code, date="2025")
        if holdings is None or holdings.empty:
            return ["暂无数据"]
        names = " ".join(holdings["股票名称"].astype(str).tolist()[:10])
        tags = {
            "CPO/光模块": ["中际旭创","新易盛","天孚通信","光库科技","源杰科技"],
            "AI算力": ["寒武纪","海光信息","浪潮信息","中科曙光","工业富联"],
            "半导体": ["中芯国际","北方华创","韦尔股份","兆易创新","卓胜微"],
            "新能源": ["宁德时代","比亚迪","隆基绿能","阳光电源","亿纬锂能"],
            "消费": ["贵州茅台","五粮液","伊利股份","海天味业","美的集团"],
            "医药": ["药明康德","恒瑞医药","迈瑞医疗","片仔癀","百济神州"],
            "金融": ["中国平安","招商银行","工商银行","中信证券","东方财富"],
            "互联网": ["腾讯","美团","阿里巴巴","京东","拼多多","百度"],
            "美股科技": ["苹果","微软","英伟达","谷歌","亚马逊","Meta","特斯拉"],
        }
        directions = []
        for direction, keywords in tags.items():
            if any(kw in names for kw in keywords):
                directions.append(direction)
        return directions if directions else ["均衡/其他"]
    except Exception:
        return ["暂无数据"]

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

@cached(ttl=3600)
def get_short_term_perf(code: str) -> dict:
    """获取短期行情：日增长率、近1周、近1月、同类排名。"""
    df = get_rank()
    if df.empty:
        return {}
    try:
        match = df[df["基金代码"].astype(str) == str(code)]
        if match.empty:
            return {}
        row = match.iloc[0]
        return {
            "排名": int(row.get("序号", 0)),
            "日涨幅": str(row.get("日增长率", "")),
            "近1周": str(row.get("近1周", "")),
            "近1月": str(row.get("近1月", "")),
            "近3月": str(row.get("近3月", "")),
            "净值": str(row.get("单位净值", "")),
            "总基金数": int(len(df)),
        }
    except Exception:
        return {}

@cached(ttl=86400)
def get_all_funds() -> pd.DataFrame:
    """全市场基金列表。"""
    try:
        return ak.fund_name_em()
    except Exception:
        return pd.DataFrame()

@cached(ttl=86400)
def get_fund_name(code: str) -> str:
    """获取基金名称（多源回退）。"""
    # Source 1: akshare
    try:
        df = get_all_funds()
        if not df.empty:
            match = df[df["基金代码"].astype(str) == str(code)]
            if not match.empty:
                return str(match.iloc[0]["基金简称"])
    except: pass

    # Source 2: pingzhongdata JS
    try:
        import urllib.request, re
        url = f"http://fund.eastmoney.com/pingzhongdata/{code}.js"
        req = urllib.request.Request(url, headers={"Referer":"http://fund.eastmoney.com/","User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            text = resp.read().decode("utf-8","replace")
        m = re.search(r'fS_name\s*=\s*"([^"]+)"', text)
        if m: return m.group(1)
    except: pass

    # Source 3: realtime API
    try:
        import urllib.request, re, json
        url = f"http://fundgz.1234567.com.cn/js/{code}.js"
        req = urllib.request.Request(url, headers={"Referer":"http://fund.eastmoney.com/","User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            text = resp.read().decode("utf-8","replace")
        m = re.search(r'jsonpgz\((\{.*\})\)', text)
        if m:
            data = json.loads(m.group(1))
            return data.get("name", code)
    except: pass

    return code

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


@cached(ttl=86400)
def get_full_holdings(code: str) -> dict:
    """获取基金全部持仓 + 地域分布比例。"""
    try:
        df = ak.fund_portfolio_hold_em(symbol=code, date="2025")
        if df is None or df.empty:
            return {"holdings": [], "region_breakdown": {}}

        # 取最新季度数据
        latest_quarter = df["季度"].iloc[0]
        latest = df[df["季度"] == latest_quarter].copy()

        holdings = []
        region_pct = {"A股": 0.0, "港股": 0.0, "美股": 0.0, "其他": 0.0}

        for _, row in latest.iterrows():
            stock_code = str(row.get("股票代码", ""))
            stock_name = str(row.get("股票名称", ""))
            pct = float(row.get("占净值比例", 0))

            # 判断市场
            if len(stock_code) == 6 and stock_code.isdigit():
                market = "A股"
            elif len(stock_code) == 5 and stock_code.startswith("0"):
                market = "港股"
            elif any(kw in stock_name for kw in ["苹果","微软","英伟达","谷歌","亚马逊","Meta","特斯拉","NVIDIA","Apple","Microsoft","Amazon"]):
                market = "美股"
            elif "-" in stock_name or any(kw in stock_name.upper() for kw in ["-S","-W","-SW"]):
                market = "港股"
            else:
                market = "其他"

            holdings.append({
                "代码": stock_code,
                "名称": stock_name,
                "占比": round(pct, 2),
                "市场": market,
            })
            region_pct[market] += pct

        # 四舍五入
        for k in region_pct:
            region_pct[k] = round(region_pct[k], 2)

        return {
            "季度": latest_quarter,
            "持仓": holdings,
            "地域分布": region_pct,
            "总占比": round(sum(r["占比"] for r in holdings), 2),
        }
    except Exception:
        return {"holdings": [], "region_breakdown": {}}


# ── FundCrawler 模式：天天基金 HTML 页面抓取 ────────────────────

@cached(ttl=86400)
def get_fund_overview(code: str) -> dict:
    """基金基本概况（天天基金 jbgk 页面 HTML 抓取）。
    返回：fund_type, fund_size(亿), fund_company, fund_value, 三项费率
    基于 Jerry1014/FundCrawler 的 tiantian.py 解析模式。
    """
    html = _fetch_html(f"http://fundf10.eastmoney.com/jbgk_{code}.html")
    if not html:
        return {}

    result = {}

    # 基金类型
    if m := re.search(r'基金类型</th><td>(.*?)</td></tr><tr><th>发行日期', html):
        result["fund_type"] = m.group(1)

    # 资产规模（亿）
    if m := re.search(fr'(?:净\s*)?资产规模</th><td>(---|{_NUMBER_RE}亿)', html):
        raw = m.group(1)
        if raw != '---':
            result["fund_size"] = raw[:-1].replace(',', '')

    # 基金管理人
    if m := re.search(r'基金管理人</th><td><a.*?">(.+?)</a></td><th>基金托管人', html):
        result["fund_company"] = m.group(1)

    # 单位净值
    if m := re.search(fr'单位净值.*?：[\s\S]*?({_NUMBER_RE})\s', html):
        result["fund_value"] = m.group(1)

    # 管理费率
    if m := re.search(fr'管理费率</th><td>(({_NUMBER_RE})%|---|<a)', html):
        val = m.group(1)
        if val != '<a':
            result["management_fee"] = '--' if val == '---' else val

    # 托管费率
    if m := re.search(fr'托管费率</th><td>(({_NUMBER_RE})%|---)', html):
        val = m.group(1)
        result["custody_fee"] = '--' if val == '---' else val

    # 销售服务费率
    if m := re.search(fr'销售服务费率</th><td>(({_NUMBER_RE})%|---)', html):
        val = m.group(1)
        result["sales_service_fee"] = '--' if val == '---' else val

    return result


@cached(ttl=86400)
def get_fund_manager_info(code: str) -> dict:
    """基金经理信息（天天基金 jjjl 页面 HTML 抓取）。
    基于 Jerry1014/FundCrawler 的 tiantian.py parse_manager 模式。
    """
    html = _fetch_html(f"http://fundf10.eastmoney.com/jjjl_{code}.html")
    if not html:
        return {}

    result = {}
    if m := re.search(r'现任基金经理简介[\s\S]+?姓名：[\s\S]+?<a.+?>(.+?)</a>', html):
        result["manager_name"] = m.group(1)
    if m := re.search(r'现任基金经理简介[\s\S]+?上任日期：[\s\S]+?>(.+?)</p>', html):
        result["appointment_date"] = m.group(1)

    return result


@cached(ttl=86400)
def get_fund_risk_data(code: str) -> dict:
    """基金风险数据（天天基金 tsdata 页面 HTML 抓取）。
    返回：近3年标准差、近3年夏普比率
    基于 Jerry1014/FundCrawler 的 tiantian.py parse_tsdata 模式。
    """
    html = _fetch_html(f"http://fundf10.eastmoney.com/tsdata_{code}.html")
    if not html:
        return {}

    result = {}
    # 近3年标准差（定位"标准差"行 → 第3个td）
    if m := re.search(
        r'<td>标准差</td><td[^>]*>.*?</td><td[^>]*>.*?</td><td[^>]*>(.*?)</td>', html
    ):
        val = m.group(1)
        result["stddev_3y"] = val if val and val != '--' else None

    # 近3年夏普比率
    if m := re.search(
        r'<td>夏普比率</td><td[^>]*>.*?</td><td[^>]*>.*?</td><td[^>]*>(.*?)</td>', html
    ):
        val = m.group(1)
        result["sharpe_3y"] = val if val and val != '--' else None

    return result


@cached(ttl=86400)
def get_fund_enriched(code: str) -> dict:
    """聚合多源基金数据：akshare + 天天基金 HTML + pingzhongdata。
    从 FundCrawler 模式整合：基本信息 + 基金经理 + 风险指标。
    """
    result = {"code": code}

    # akshare 基本信息
    try:
        info = get_fund_info(code) or {}
        result["name"] = info.get("基金简称", "")
    except Exception:
        pass

    # FundCrawler 模式：天天基金 HTML
    overview = get_fund_overview(code)
    manager = get_fund_manager_info(code)
    risk = get_fund_risk_data(code)

    result.update({f"tt_{k}": v for k, v in overview.items()})
    result.update({f"tt_{k}": v for k, v in manager.items()})
    result.update({f"tt_{k}": v for k, v in risk.items()})

    return result
