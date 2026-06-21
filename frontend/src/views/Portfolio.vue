<template>
  <div class="page">
    <h1 class="page-title">⚖️ 仓位配比</h1>
    <p class="page-subtitle">三种优化方法 · 科学计算最优仓位分配</p>

    <div class="card">
      <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end">
        <div style="flex:1;min-width:300px">
          <label>基金代码（逗号分隔）</label>
          <input v-model="codes" placeholder="001513, 270042, 050025">
        </div>
        <div>
          <label>优化方法</label>
          <select v-model="method" style="width:160px">
            <option value="max_sharpe">最大夏普比率</option>
            <option value="min_var">最小方差</option>
            <option value="risk_parity">风险平价</option>
          </select>
        </div>
        <button class="btn btn-primary" @click="run" :disabled="loading">{{ loading ? '计算中…' : '🎯 开始优化' }}</button>
      </div>
    </div>

    <div v-if="loading" class="loading">优化计算中…</div>

    <div v-if="result && !result.error" class="card">
      <div class="stat-grid">
        <div class="stat-card">
          <div class="label">预期年化收益</div>
          <div class="value" style="color:var(--green)">{{ (result.expected_return*100).toFixed(2) }}%</div>
        </div>
        <div class="stat-card">
          <div class="label">预期年化波动</div>
          <div class="value">{{ (result.expected_vol*100).toFixed(2) }}%</div>
        </div>
        <div class="stat-card">
          <div class="label">夏普比率</div>
          <div class="value" style="color:var(--brand)">{{ result.sharpe }}</div>
        </div>
      </div>
      <h3 style="margin:16px 0 8px">最优权重分配</h3>
      <div v-for="(w, code) in result.weights" :key="code" style="display:flex;align-items:center;gap:12px;margin:8px 0">
        <span style="width:100px;font-weight:600">{{ code }}</span>
        <div style="flex:1;height:24px;background:#f0f0f0;border-radius:12px;overflow:hidden">
          <div :style="{width: (w*100)+'%', height:'100%', background:'linear-gradient(90deg, #3b82f6, #60a5fa)', borderRadius:'12px', transition:'width .5s'}"></div>
        </div>
        <span style="font-weight:700;width:60px;text-align:right">{{ (w*100).toFixed(1) }}%</span>
      </div>
    </div>

    <div v-if="result?.error" class="card"><div class="empty-state"><div class="icon">⚠️</div><div class="title">{{ result.error }}</div></div></div>

    <div class="card" v-if="!result && !loading">
      <div class="empty-state"><div class="icon">⚖️</div><div class="title">输入基金代码开始优化</div><div class="desc">至少需要2只基金</div></div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref } from "vue"
import { api } from "../api"
const codes = ref(""), method = ref("max_sharpe"), result = ref<any>(null), loading = ref(false)
async function run() {
  loading.value = true
  const codeList = codes.value.split(/[,，\s]+/).filter(Boolean)
  result.value = await api.optimize(codeList, method.value)
  loading.value = false
}
</script>
