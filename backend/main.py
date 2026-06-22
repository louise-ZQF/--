"""FastAPI 入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import holdings, watchlist, portfolio, screener, backtest, assistant, fund, realtime
from db import init_db

app = FastAPI(title="基金选择网站 API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"], allow_headers=["*"],
)

init_db()
app.include_router(holdings.router,  prefix="/api/holdings",  tags=["持仓"])
app.include_router(watchlist.router, prefix="/api/watchlist", tags=["自选"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["配比"])
app.include_router(screener.router,  prefix="/api/screener",  tags=["筛选"])
app.include_router(backtest.router,  prefix="/api/backtest",  tags=["回测"])
app.include_router(assistant.router, prefix="/api/ai",        tags=["AI"])
app.include_router(fund.router,     prefix="/api/fund",     tags=["基金"])
app.include_router(realtime.router, prefix="/api/realtime", tags=["实时"])

@app.get("/")
def root():
    return {"ok": True, "app": "基金选择网站"}
