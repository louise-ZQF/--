import axios from "axios"
const http = axios.create({ baseURL: "/api", timeout: 180000 })

export const api = {
  // 持仓
  analyzeHoldings: (items:any[]) => http.post("/holdings/analyze", items).then(r=>r.data),
  batchImport: (items:any[]) => http.post("/holdings/batch-import", items).then(r=>r.data),
  listHoldings: () => http.get("/holdings/list").then(r=>r.data),
  saveHolding: (item:any) => http.post("/holdings/save", item).then(r=>r.data),
  delHolding: (code:string) => http.delete(`/holdings/del?code=${code}`).then(r=>r.data),
  // 自选
  listWatch: () => http.get("/watchlist/list").then(r=>r.data),
  addWatch: (code:string) => http.post(`/watchlist/add?code=${code}`),
  delWatch: (code:string) => http.delete(`/watchlist/del?code=${code}`),
  watchSignal: () => http.get("/watchlist/signal").then(r=>r.data),
  // 配比
  optimize: (codes:string[], method:string) => http.post("/portfolio/optimize",{codes,method}).then(r=>r.data),
  // 筛选
  screen4433: () => http.get("/screener/4433").then(r=>r.data),
  scoreFund: (code:string) => http.get(`/screener/score?code=${code}`).then(r=>r.data),
  // 回测
  dca: (code:string,amount:number,freq:string) => http.post("/backtest/dca",{code,amount,freq}).then(r=>r.data),
  // AI
  ask: (question:string,code?:string) => http.post("/ai/chat",{question,code}).then(r=>r.data),
}
