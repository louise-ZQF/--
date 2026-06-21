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
          <span style="font-size:28px">{{ s.can_buy ? '✅' : '⏳' }}</span>
          <div style="flex:1">
            <b style="font-size:15px">{{ s.name || s.code }}</b>
            <span style="color:var(--muted);font-size:12px;margin-left:8px">{{ s.code }}</span>
            <div style="font-size:13px;margin-top:4px;white-space:pre-line;line-height:1.6">{{ s.reason }}</div>
          </div>
          <button class="btn btn-danger" @click="remove(s.code)" style="font-size:11px">移除</button>
        </div>

        <!-- Condition checklist -->
        <div style="margin-top:10px;padding-top:10px;border-top:1px solid var(--line)">
          <div v-for="(check, label) in s.checks" :key="label"
            style="display:flex;align-items:center;gap:8px;padding:4px 0;font-size:13px">
            <span>{{ check.pass ? '✅' : '❌' }}</span>
            <span style="flex:1">{{ label }}</span>
            <span :style="{color: check.pass ? 'var(--green)' : 'var(--red)'}">{{ check.value }}</span>
          </div>
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

    <div class="card" style="margin-top:20px">
      <details style="cursor:pointer">
        <summary style="font-weight:600;font-size:15px;margin-bottom:12px">📖 术语解释</summary>
        <div style="font-size:13px;color:var(--ink-secondary);line-height:1.8;padding-top:8px">
          <p><b>估值偏低(分位&lt;35%)</b>：当前净值处于近3年较低位置，买入性价比相对较高。</p>
          <p><b>已回调(距高点&lt;-10%)</b>：基金净值从近1年最高点回落超过10%，出现像样回调。</p>
          <p><b>未超买(RSI&lt;60)</b>：短期未出现过热，买入后短期回调风险相对可控。</p>
          <p><b>趋势非向下</b>：中期均线未持续走低，避免在下跌趋势中接飞刀。</p>
          <p><b>四维判断</b>：四项条件全部满足=✅可考虑买入。任一不满足=暂不建议，等条件改善。</p>
        </div>
      </details>
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
