from fastapi import APIRouter
from pydantic import BaseModel
import os, requests
from services.data import get_nav
from services.metrics import nav_percentile, rsi, trend_ma

router = APIRouter()

class ChatReq(BaseModel):
    question: str
    code: str | None = None

@router.post("/chat")
def chat(req: ChatReq):
    context = ""
    if req.code:
        df = get_nav(req.code)
        if not df.empty:
            nav = df["nav"]
            pct = nav_percentile(nav)
            r = rsi(nav)
            tr = trend_ma(nav)
            context = f"基金{req.code}: 净值分位{pct:.0%}, RSI{r:.0f}, 趋势{tr}。"

    prompt = f"你是基金投研助手,只依据给定数据作答,不杜撰,不预测涨跌,结尾注明非投资建议。\n数据:{context}\n用户:{req.question}"
    key = os.environ.get("LLM_API_KEY", "")
    if not key:
        return {"answer": "AI 未配置 (设置 LLM_API_KEY 环境变量)"}

    try:
        resp = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": "deepseek-chat", "messages": [{"role":"user","content":prompt}]},
            timeout=60,
        ).json()
        return {"answer": resp["choices"][0]["message"]["content"]}
    except Exception as e:
        return {"answer": f"AI 调用失败: {e}"}
