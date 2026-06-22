import { createRouter, createWebHashHistory } from "vue-router"

const routes = [
  { path: "/", redirect: "/holdings" },
  { path: "/holdings", name: "holdings", component: () => import("../views/Holdings.vue") },
  { path: "/watchlist", name: "watchlist", component: () => import("../views/Watchlist.vue") },
  { path: "/realtime", name: "realtime", component: () => import("../views/Realtime.vue") },
  { path: "/screener", name: "screener", component: () => import("../views/Screener.vue") },
]

export default createRouter({ history: createWebHashHistory(), routes })
