<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="logo" @click="$router.push('/')">
        <span class="logo-text">FundPicker</span>
      </div>
      <nav class="nav">
        <router-link v-for="m in menu" :key="m.path" :to="m.path" class="nav-item" active-class="nav-active">
          <span class="nav-dot" v-if="$route.path===m.path"></span>
          <span class="nav-icon">{{ m.icon }}</span>
          <span class="nav-label">{{ m.label }}</span>
        </router-link>
      </nav>
    </aside>
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
const menu = [
  { path: "/holdings", icon: "", label: "持仓" },
  { path: "/watchlist", icon: "", label: "自选" },
  { path: "/realtime", icon: "", label: "实时" },
  { path: "/screener", icon: "", label: "筛选" },
]
</script>

<style scoped>
.app-shell { display: flex; min-height: 100vh; }
.sidebar {
  width: 240px; background: rgba(255,255,255,.8);
  backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
  border-right: 1px solid var(--line); display: flex; flex-direction: column;
  padding: 24px 0; flex-shrink: 0; position: sticky; top: 0; height: 100vh;
}
.logo { display: flex; align-items: center; gap: 10px; padding: 0 20px 20px; border-bottom: 1px solid var(--line); cursor: pointer; }
.logo-icon { font-size: 24px; }
.logo-text { font-size: 17px; font-weight: 700; letter-spacing: -0.3px; }
.nav { flex: 1; padding: 16px 12px; }
.nav-item {
  display: flex; align-items: center; gap: 10px; padding: 10px 14px;
  color: var(--ink-secondary); text-decoration: none; font-size: 14px; font-weight: 450;
  border-radius: var(--radius-sm); margin-bottom: 2px; transition: all var(--transition);
  position: relative;
}
.nav-item:hover { background: #f0f0f3; color: var(--ink); }
.nav-active { background: #f0f0f3; color: var(--ink); font-weight: 550; }
.nav-icon { font-size: 18px; width: 24px; text-align: center; }
.nav-label { letter-spacing: -0.01em; }
.main-content { flex: 1; overflow-y: auto; min-height: 100vh; }
@media (max-width: 768px) { .sidebar { width: 72px; } .logo-text, .nav-label { display: none; } .nav-item { justify-content: center; padding: 12px; } }
</style>
