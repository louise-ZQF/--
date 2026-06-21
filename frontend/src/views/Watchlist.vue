<template>
  <div class="page">
    <h1 class="page-title">⭐ 自选监控</h1>
    <p class="page-subtitle">智能买点提醒 · 估值/回撤/RSI/趋势 四维判断</p>

    <div class="card">
      <div style="display:flex;gap:10px">
        <input v-model="newCode" placeholder="基金代码, 如 001513" style="flex:1;max-width:200px">
        <button class="btn btn-primary" @click="add">＋ 添加自选</button>
        <button class="btn" @click="checkSignals" :disabled="loading">
          {{ loading ? '检查中…' : '🔄 刷新信号' }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading">检查买入信号…</div>

    <div v-if="signals.length">
      <div class="card" v-for="s in signals" :key="s.code">
        <div class="signal-row" :class="s.can_buy ? 'signal-buy' : 'signal-wait'">
          <span style="font-size:24px">{{ s.can_buy ? '✅' : '⏳' }}</span>
          <div style="flex:1">
            <b>{{ s.code }}</b>
            <div style="font-size:13px;margin-top:2px">{{ s.reason }}</div>
            <div style="font-size:12px;color:var(--muted);margin-top:4px">{{ s.detail }}</div>
          </div>
          <button class="btn btn-danger" @click="remove(s.code)" style="font-size:11px">移除</button>
        </div>
        <!-- Mini stat bars -->
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:12px;padding-top:12px;border-top:1px solid var(--line)">
          <div><div style="font-size:11px;color:var(--muted)">估值分位</div><div style="font-weight:700">{{ (s.percentile*100).toFixed(0) }}%</div></div>
          <div><div style="font-size:11px;color:var(--muted)">距高点</div><div style="font-weight:700" :style="{color:s.drawdown<-0.1?'var(--green)':'var(--amber)'}">{{ (s.drawdown*100).toFixed(0) }}%</div></div>
          <div><div style="font-size:11px;color:var(--muted)">RSI</div><div style="font-weight:700" :style="{color:s.rsi<60?'var(--green)':'var(--red)'}">{{ s.rsi }}</div></div>
          <div><div style="font-size:11px;color:var(--muted)">趋势</div><div style="font-weight:700">{{ s.trend }}</div></div>
        </div>
      </div>
    </div>

    <div class="card" v-if="!signals.length && !loading && watchlist.length">
      <div class="empty-state">
        <div class="icon">🔔</div>
        <div class="title">点击"刷新信号"查看买点</div>
      </div>
    </div>

    <div class="card" v-if="!watchlist.length && !loading">
      <div class="empty-state">
        <div class="icon">⭐</div>
        <div class="title">还没有自选基金</div>
        <div class="desc">添加你关注的基金，智能监控买入时机</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue"
import { api } from "../api"

const newCode = ref("")
const watchlist = ref<any[]>([])
const signals = ref<any[]>([])
const loading = ref(false)

onMounted(async () => { watchlist.value = await api.listWatch() })

async function add() {
  if (!newCode.value) return
  await api.addWatch(newCode.value)
  newCode.value = ""
  watchlist.value = await api.listWatch()
}

async function remove(code: string) {
  await api.delWatch(code)
  watchlist.value = await api.listWatch()
  signals.value = signals.value.filter(s => s.code !== code)
}

async function checkSignals() {
  loading.value = true
  signals.value = await api.watchSignal()
  loading.value = false
}
</script>
