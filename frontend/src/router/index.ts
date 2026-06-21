import { createRouter, createWebHashHistory } from "vue-router"

const routes = [
  { path: "/", redirect: "/holdings" },
  { path: "/holdings", name: "holdings", component: () => import("../views/Holdings.vue") },
  { path: "/watchlist", name: "watchlist", component: () => import("../views/Watchlist.vue") },
  { path: "/portfolio", name: "portfolio", component: () => import("../views/Portfolio.vue") },
  { path: "/screener", name: "screener", component: () => import("../views/Screener.vue") },
  { path: "/backtest", name: "backtest", component: () => import("../views/Backtest.vue") },
  { path: "/assistant", name: "assistant", component: () => import("../views/Assistant.vue") },
]

export default createRouter({ history: createWebHashHistory(), routes })
