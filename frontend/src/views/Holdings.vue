<template>
  <div class="page">
    <h1 class="page-title">💼 持仓分析</h1>
    <p class="page-subtitle">导入持仓 · 分析投资方向 · 被动/主动配置建议</p>

    <!-- Import -->
    <div class="card">
      <p style="font-size:13px;color:var(--ink-secondary);margin-bottom:12px">每行一个基金代码，无需输入金额</p>
      <textarea v-model="batchText" rows="4" placeholder="001513&#10;270042&#10;050025&#10;110020" style="width:100%;font-family:monospace;font-size:14px"></textarea>
      <div style="display:flex;gap:10px;margin-top:12px">
        <button class="btn btn-primary" @click="batchImport" :disabled="loading">
          {{ loading ? '分析中…' : '📥 导入并分析' }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading">分析中…</div>

    <!-- Portfolio Summary -->
    <div v-if="portfolio.summary" class="card">
      <div class="stat-grid">
        <div class="stat-card"><div class="label">持仓数量</div><div class="value">{{ portfolio.summary.total }}</div><div class="sub">被动{{ portfolio.summary.passive_count }} · 主动{{ portfolio.summary.active_count }}</div></div>
        <div class="stat-card"><div class="label">平均估值分位</div><div class="value" :style="{color:portfolio.summary.avg_percentile<0.5?'var(--green)':'var(--amber)'}">{{ (portfolio.summary.avg_percentile*100).toFixed(0) }}%</div></div>
        <div class="stat-card"><div class="label">投资方向</div><div class="sub" style="font-size:13px">{{ (portfolio.summary.directions||[]).join(' · ') }}</div></div>
      </div>
      <div class="advice-box advice-info">{{ portfolio.summary.portfolio_advice }}</div>
    </div>

    <!-- Per-fund cards -->
    <div v-if="portfolio.funds?.length" style="margin-top:16px">
      <div class="stat-grid">
        <div class="stat-card" v-for="f in portfolio.funds" :key="f.code">
          <div class="label">{{ f.fund_type }} · {{ f.region }}</div>
          <div style="font-size:16px;font-weight:600;margin:4px 0">{{ f.name }}</div>
          <div style="font-size:12px;color:var(--ink-secondary);margin-bottom:8px">{{ f.code }}</div>
          <div style="display:flex;gap:4px;flex-wrap:wrap;margin-bottom:8px">
            <span v-for="d in f.direction" :key="d" class="badge badge-blue" style="font-size:10px">{{ d }}</span>
          </div>
          <div class="advice-box" :class="f.passive_score>60?'advice-buy':f.passive_score>35?'advice-info':'advice-wait'">
            {{ f.advice }}
          </div>
          <div style="display:flex;gap:16px;margin-top:10px;font-size:12px;color:var(--ink-secondary)">
            <span>估值分位 {{ (f.percentile*100).toFixed(0) }}%</span>
            <span>RSI {{ f.rsi }}</span>
            <span>趋势 {{ f.trend }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty -->
    <div class="card" v-if="!portfolio.funds?.length && !loading">
      <div class="empty-state"><div class="icon">💼</div><div class="title">导入你的持仓</div><div class="desc">粘贴基金代码，智能分析投资方向与配置建议</div></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue"
import { api } from "../api"

const batchText = ref("")
const portfolio = ref<any>({})
const loading = ref(false)

async function batchImport() {
  const codes = batchText.value.trim().split(/[\n,，\s]+/).filter(c => c.length === 6)
  if (!codes.length) return
  loading.value = true
  const items = codes.map(c => ({ code: c, name: "" }))
  portfolio.value = await api.analyzeHoldings(items)
  loading.value = false
}
</script>
