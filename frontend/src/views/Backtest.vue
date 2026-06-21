<template>
  <div class="page">
    <h1 class="page-title">📊 定投回测</h1>
    <p class="page-subtitle">模拟历史定投 · 看清真实收益与最大回撤</p>

    <div class="card">
      <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end">
        <div><label>基金代码</label><input v-model="code" placeholder="001513" style="width:140px"></div>
        <div><label>每期金额(元)</label><input v-model.number="amount" type="number" style="width:120px"></div>
        <div><label>频率</label><select v-model="freq" style="width:100px"><option value="D">每日</option><option value="W">每周</option><option value="M">每月</option></select></div>
        <button class="btn btn-primary" @click="run" :disabled="loading">{{ loading ? '回测中…' : '📈 开始回测' }}</button>
      </div>
    </div>

    <div v-if="loading" class="loading">回测计算中…</div>

    <div v-if="result && !result.error">
      <div class="stat-grid">
        <div class="stat-card"><div class="label">累计投入</div><div class="value">¥{{ result.total_invested?.toLocaleString() }}</div></div>
        <div class="stat-card"><div class="label">最终市值</div><div class="value" :style="{color:result.total_return>0?'var(--green)':'var(--red)'}">¥{{ result.final_value?.toLocaleString() }}</div></div>
        <div class="stat-card"><div class="label">总收益率</div><div class="value" :style="{color:result.total_return>0?'var(--green)':'var(--red)'}">{{ (result.total_return*100).toFixed(2) }}%</div></div>
        <div class="stat-card"><div class="label">年化收益</div><div class="value">{{ (result.annualized*100).toFixed(2) }}%</div></div>
        <div class="stat-card"><div class="label">最大回撤</div><div class="value" style="color:var(--red)">{{ (result.max_drawdown*100).toFixed(2) }}%</div></div>
      </div>
      <div class="card" v-if="result.curve?.length">
        <NavChart :data="result.curve" />
      </div>
    </div>

    <div v-if="result?.error" class="card"><div class="empty-state"><div class="icon">⚠️</div><div class="title">{{ result.error }}</div></div></div>

    <div class="card" v-if="!result && !loading">
      <div class="empty-state"><div class="icon">📊</div><div class="title">输入基金代码开始回测</div><div class="desc">模拟历史定投，看清真实收益</div></div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref } from "vue"
import { api } from "../api"
import NavChart from "../components/NavChart.vue"
const code = ref("001513"), amount = ref(1000), freq = ref("W"), result = ref<any>(null), loading = ref(false)
async function run() { loading.value = true; result.value = await api.dca(code.value, amount.value, freq.value); loading.value = false }
</script>
