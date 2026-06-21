"""akshare 数据封装 + 统一缓存"""
import akshare as ak
import pandas as pd
from cache import cached


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
