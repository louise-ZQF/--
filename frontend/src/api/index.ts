import axios from "axios"

// 后端地址：把下面这行改成你的 Render 后端地址即可
// 例如: const API_HOST = "https://fund-picker.onrender.com"
const API_HOST = ""

const http = axios.create({
  baseURL: API_HOST ? API_HOST + "/api" : "/api",
  timeout: 180000
})

export const api = {
  analyzeHoldings: (items:any[]) => http.post("/holdings/analyze", items).then(r=>r.data),
  batchImport: (items:any[]) => http.post("/holdings/batch-import", items).then(r=>r.data),
  listHoldings: () => http.get("/holdings/list").then(r=>r.data),
  saveHolding: (item:any) => http.post("/holdings/save", item).then(r=>r.data),
  delHolding: (code:string) => http.delete(`/holdings/del?code=${code}`).then(r=>r.data),
  listWatch: () => http.get("/watchlist/list").then(r=>r.data),
  addWatch: (code:string) => http.post(`/watchlist/add?code=${code}`),
  delWatch: (code:string) => http.delete(`/watchlist/del?code=${code}`),
  watchSignal: () => http.get("/watchlist/signal").then(r=>r.data),
  optimize: (codes:string[], method:string) => http.post("/portfolio/optimize",{codes,method}).then(r=>r.data),
  screen4433: () => http.get("/screener/4433").then(r=>r.data),
  scoreFund: (code:string) => http.get(`/screener/score?code=${code}`).then(r=>r.data),
  dca: (code:string,amount:number,freq:string) => http.post("/backtest/dca",{code,amount,freq}).then(r=>r.data),
  ask: (question:string,code?:string) => http.post("/ai/chat",{question,code}).then(r=>r.data),
  fundHoldings: (code:string) => http.get('/fund/holdings', {params:{code}}).then(r=>r.data),
  realtime: (filter:string='all') => http.get('/realtime', {params:{filter}}).then(r=>r.data),
}
