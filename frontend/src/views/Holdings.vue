<template>
  <div class="page">
    <h1 class="page-title">💼 持仓分析</h1>
    <p class="page-subtitle">智能定投建议 · 基于真实净值与估值分位</p>

    <!-- Add form -->
    <div class="card">
      <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end">
        <div><label>基金代码</label><input v-model="form.code" placeholder="001513" style="width:120px"></div>
        <div><label>成本净值</label><input v-model.number="form.cost" type="number" step="0.01" style="width:120px"></div>
        <div><label>持有份额</label><input v-model.number="form.shares" type="number" step="0.01" style="width:120px"></div>
        <div><label>名称(可选)</label><input v-model="form.name" placeholder="自动获取" style="width:160px"></div>
        <button class="btn btn-primary" @click="addHolding">＋ 添加</button>
      </div>
    </div>

    <!-- Holdings list -->
    <div v-if="holdings.length" class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <span style="font-weight:700">我的持仓 ({{ holdings.length }}只)</span>
        <button class="btn btn-primary" @click="analyze" :disabled="loading">
          {{ loading ? '分析中…' : '🔬 分析全部' }}
        </button>
      </div>
      <table>
        <thead><tr><th>代码</th><th>名称</th><th>成本</th><th>份额</th><th></th></tr></thead>
        <tbody>
          <tr v-for="h in holdings" :key="h.code">
            <td>{{ h.code }}</td><td>{{ h.name || '—' }}</td>
            <td>{{ h.cost }}</td><td>{{ h.shares }}</td>
            <td><button class="btn btn-danger" @click="removeHolding(h.code)">删除</button></td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading">正在分析…</div>

    <!-- Results -->
    <div v-if="results.length">
      <div class="stat-grid">
        <div class="stat-card" v-for="r in results" :key="r.code">
          <div class="label">{{ r.name || r.code }}</div>
          <div class="value" :style="{color: r.return > 0 ? 'var(--green)' : 'var(--red)'}">
            {{ (r.return*100).toFixed(1) }}%
          </div>
          <div class="sub">净值 {{ r.current_nav }} · 回撤 {{ (r.max_drawdown*100).toFixed(1) }}%</div>
          <NavChart v-if="r.nav_data?.length" :data="r.nav_data" />
          <div class="advice-box" :class="r.advice.includes('加大') ? 'advice-buy' : r.advice.includes('暂缓') ? 'advice-wait' : 'advice-info'" style="margin-top:8px">
            <b>{{ r.advice }}</b>
            <div style="font-size:12px;margin-top:4px">{{ r.reason }}</div>
          </div>
          <div style="display:flex;gap:12px;margin-top:8px;font-size:12px">
            <span>估值分位: {{ (r.percentile*100).toFixed(0) }}%</span>
            <span>趋势: {{ r.trend }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div class="card" v-if="!holdings.length && !loading">
      <div class="empty-state">
        <div class="icon">📋</div>
        <div class="title">还没有持仓数据</div>
        <div class="desc">添加你的第一只基金，开始智能分析</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue"
import { api } from "../api"
import NavChart from "../components/NavChart.vue"

const form = ref({ code: "", cost: 0, shares: 0, name: "" })
const holdings = ref<any[]>([])
const results = ref<any[]>([])
const loading = ref(false)

onMounted(async () => { holdings.value = await api.listHoldings() })

async function addHolding() {
  if (!form.value.code) return
  await api.saveHolding(form.value)
  form.value = { code: "", cost: 0, shares: 0, name: "" }
  holdings.value = await api.listHoldings()
}

async function removeHolding(code: string) {
  await api.delHolding(code)
  holdings.value = await api.listHoldings()
}

async function analyze() {
  loading.value = true
  results.value = await api.analyzeHoldings(holdings.value)
  loading.value = false
}
</script>
