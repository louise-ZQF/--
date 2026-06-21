<template>
  <div class="page">
    <h1 class="page-title">🔍 基金筛选</h1>
    <p class="page-subtitle">4433法则选基 · 经理风格评分</p>

    <div class="card">
      <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">
        <button v-for="r in regions" :key="r.value"
          class="btn" :class="{'btn-primary': selectedRegion===r.value}"
          @click="selectedRegion=r.value; screen()">
          {{ r.label }}
        </button>
      </div>
      <div style="display:flex;gap:10px;align-items:flex-end">
        <button class="btn btn-primary" @click="screen" :disabled="loading">{{ loading ? '筛选中…' : '🔍 4433 筛选' }}</button>
        <div style="flex:1"></div>
        <input v-model="scoreCode" placeholder="代码评分" style="width:140px">
        <button class="btn" @click="score" :disabled="scoring">{{ scoring ? '评分中…' : '📊 评分' }}</button>
      </div>
    </div>

    <div v-if="loading" class="loading">正在筛选全市场基金…</div>

    <div v-if="results.length" class="card">
      <h3 style="margin-bottom:12px">4433 精选基金 ({{ results.length }}只)</h3>
      <table>
        <thead><tr>
          <th>代码</th><th>简称</th><th>地区</th><th>投资方向</th>
          <th>近1年</th><th>近3年</th>
          <th>买入时机</th>
          <th></th>
        </tr></thead>
        <tbody>
          <tr v-for="f in results.slice(0,30)" :key="f['基金代码']||f.code">
            <td>{{ f['基金代码']||f.code }}</td>
            <td>{{ f['基金简称']||f.name }}</td>
            <td>{{ f.region_label||'—' }}</td>
            <td>
              <span v-for="d in (f.direction||[])" :key="d" class="badge badge-blue" style="margin:1px;font-size:10px">{{ d }}</span>
            </td>
            <td :style="{color:parseFloat(f.y1)>0?'var(--green)':'var(--red)'}">{{ f.y1 }}%</td>
            <td :style="{color:parseFloat(f.y3)>0?'var(--green)':'var(--red)'}">{{ f.y3 }}%</td>
            <td>
              <span v-if="f.timing" :style="{color:f.timing.color,fontWeight:'600',fontSize:'13px'}">{{ f.timing.label }}</span>
              <span v-else style="color:var(--muted)">—</span>
              <div v-if="f.timing?.reason" style="font-size:11px;color:var(--muted)">{{ f.timing.reason }}</div>
            </td>
            <td>
              <button class="btn" style="font-size:11px;padding:4px 10px" @click="addToWatch(f)">⭐ 加自选</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="scoreResult && !scoreResult.error" class="card">
      <h3>评分: {{ scoreResult.code }}</h3>
      <div class="stat-grid">
        <div class="stat-card"><div class="label">综合评分</div><div class="value" :style="{color:scoreResult.rating==='契合'?'var(--green)':'var(--amber)'}">{{ scoreResult.score }}</div><div class="sub">{{ scoreResult.rating }}</div></div>
        <div class="stat-card" v-for="(v,k) in scoreResult.detail" :key="k"><div class="label">{{ k }}</div><div class="value" style="font-size:22px">{{ v }}</div></div>
      </div>
    </div>

    <div class="card" v-if="!results.length && !loading && !scoreResult">
      <div class="empty-state"><div class="icon">🔍</div><div class="title">点击"4433 筛选"查看精选基金</div></div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref } from "vue"
import { api } from "../api"
const results = ref<any[]>([]), loading = ref(false)
const scoreCode = ref(""), scoreResult = ref<any>(null), scoring = ref(false)
const selectedRegion = ref("all")
const regions = [
  {value:"all", label:"🌍 全部"},
  {value:"china", label:"🇨🇳 中国(A股+港股)"},
  {value:"overseas", label:"🌏 海外(美股+日韩)"},
]
async function screen() {
  loading.value = true
  const resp = await fetch(`/api/screener/4433-full?region=${selectedRegion.value}`).then(r=>r.json())
  results.value = resp
  loading.value = false
}
async function score() { scoring.value = true; scoreResult.value = await api.scoreFund(scoreCode.value); scoring.value = false }
async function addToWatch(f: any) {
  const code = f['基金代码'] || f.code
  await api.addWatch(code)
  alert(`已添加 ${code} 到自选 ✅ 去「自选监控」查看买入分析`)
}
</script>
