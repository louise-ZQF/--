<template>
  <div class="app-container">
    <aside class="sidebar">
      <div class="logo" @click="$router.push('/')">
        <span class="logo-icon">📈</span>
        <span class="logo-text">FundPicker</span>
      </div>
      <nav class="nav">
        <router-link v-for="item in menu" :key="item.path" :to="item.path" class="nav-item" active-class="nav-active">
          <span class="nav-icon">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
        </router-link>
      </nav>
      <div class="sidebar-footer">
        <div class="version">v1.0 · 仅供研究</div>
      </div>
    </aside>
    <main class="main">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
const menu = [
  { path: "/holdings", icon: "💼", label: "持仓分析" },
  { path: "/watchlist", icon: "⭐", label: "自选监控" },
  { path: "/portfolio", icon: "⚖️", label: "仓位配比" },
  { path: "/screener", icon: "🔍", label: "基金筛选" },
  { path: "/backtest", icon: "📊", label: "定投回测" },
  { path: "/assistant", icon: "🤖", label: "AI 助手" },
]
</script>

<style scoped>
.app-container { display: flex; min-height: 100vh; }
.sidebar { width: 220px; background: #fff; border-right: 1px solid var(--line); display: flex; flex-direction: column; padding: 20px 0; flex-shrink: 0; }
.logo { display: flex; align-items: center; gap: 10px; padding: 0 20px 20px; border-bottom: 1px solid var(--line); cursor: pointer; }
.logo-icon { font-size: 26px; }
.logo-text { font-size: 18px; font-weight: 750; letter-spacing: -.3px; }
.nav { flex: 1; padding: 12px 0; }
.nav-item { display: flex; align-items: center; gap: 10px; padding: 10px 20px; color: var(--muted); text-decoration: none; font-size: 14px; font-weight: 500; transition: all .15s; border-left: 3px solid transparent; }
.nav-item:hover { background: #f9fafb; color: var(--ink); }
.nav-active { color: var(--brand) !important; background: var(--brand-light); border-left-color: var(--brand); font-weight: 600; }
.nav-icon { font-size: 18px; width: 24px; text-align: center; }
.sidebar-footer { padding: 16px 20px; border-top: 1px solid var(--line); }
.version { font-size: 11px; color: var(--muted); }
.main { flex: 1; overflow-y: auto; }
@media (max-width: 768px) { .sidebar { width: 64px; } .logo-text, .nav-item span:last-child, .version { display: none; } .logo { justify-content: center; padding: 0 0 16px; } .nav-item { justify-content: center; padding: 12px; } }
</style>
