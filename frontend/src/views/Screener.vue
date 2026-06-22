<template>
  <div class="page">
    <h1 class="page-title">基金筛选</h1>
    <p class="page-subtitle">4433法则选基 · 经理风格评分</p>

    <div class="card">
      <div style="display:flex;gap:10px;align-items:flex-end">
        <button class="btn btn-primary" @click="fetchAll" :disabled="loading">{{ loading ? '加载中…' : '刷新' }}</button>
        <div style="flex:1"></div>
        <input v-model="scoreCode" placeholder="代码评分" style="width:140px">
        <button class="btn" @click="score" :disabled="scoring">{{ scoring ? '评分中…' : '评分' }}</button>
      </div>
    </div>

    <div style="display:flex;gap:10px;margin-bottom:12px;margin-top:8px">
      <button class="btn" :class="{'btn-primary': selectedRegionFilter==='china'}" @click="toggleRegionFilter('china')">中国</button>
      <button class="btn" :class="{'btn-primary': selectedRegionFilter==='overseas'}" @click="toggleRegionFilter('overseas')">海外</button>
    </div>

    <div v-if="loading" class="loading">正在加载基金数据…</div>

    <div v-if="filteredResults.length" class="card">
      <h3 style="margin-bottom:12px">4433 精选基金 ({{ filteredResults.length }}只)</h3>
      <table>
        <thead><tr>
          <th>代码</th><th>简称</th><th>地区</th><th>投资方向</th>
          <th>近1年</th><th>近3年</th>
          <th>短期表现</th><th>排名</th>
          <th>买入时机</th>
          <th></th>
        </tr></thead>
        <tbody>
          <tr v-for="f in filteredResults.slice(0,30)" :key="f['基金代码']||f.code">
            <td>{{ f['基金代码']||f.code }}</td>
            <td>{{ f['基金简称']||f.name }}</td>
            <td>{{ f.region_label||'—' }}</td>
            <td>
              <span v-for="d in (f.direction||[])" :key="d" class="badge badge-blue" style="margin:1px;font-size:10px">{{ d }}</span>
            </td>
            <td :style="{color:parseFloat(f.y1)>0?'var(--green)':'var(--red)'}">{{ f.y1 }}%</td>
            <td :style="{color:parseFloat(f.y3)>0?'var(--green)':'var(--red)'}">{{ f.y3 }}%</td>
            <td style="font-size:11px;white-space:nowrap">
              <span v-if="f.perf" :style="{color:f.perf.daily>=0?'var(--green)':'var(--red)'}">{{ f.perf.daily }}%</span>
              <span v-if="f.perf" style="color:var(--muted)"> / </span>
              <span v-if="f.perf" :style="{color:f.perf.week_1>=0?'var(--green)':'var(--red)'}">{{ f.perf.week_1 }}%</span>
              <span v-else style="color:var(--muted)">—</span>
            </td>
            <td style="font-size:12px">
              <span v-if="f.perf">{{ f.perf.rank }}/{{ f.perf.total_funds }}</span>
              <span v-else style="color:var(--muted)">—</span>
            </td>
            <td>
              <span v-if="f.timing" :style="{color:f.timing.color,fontWeight:'600',fontSize:'13px'}">{{ f.timing.label }}</span>
              <span v-else style="color:var(--muted)">—</span>
              <div v-if="f.timing?.reason" style="font-size:11px;color:var(--muted)">{{ f.timing.reason }}</div>
            </td>
            <td>
              <button v-if="!watchlistCodes.has(f['基金代码']||f.code)"
                class="btn" style="font-size:11px;padding:4px 10px"
                @click="addToWatch(f)">加自选</button>
              <span v-else style="font-size:11px;color:var(--muted)">已添加</span>
            </td>
            <td><FundHoldings :code="f['基金代码']||f.code" /></td>
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

    <div class="card" v-if="!allResults.length && !loading && !scoreResult">
      <div class="empty-state"><div class="title">加载完成，暂无数据</div></div>
    </div>

    <div class="card" style="margin-top:20px">
      <details style="cursor:pointer">
        <summary style="font-weight:600;font-size:15px;margin-bottom:12px">术语解释</summary>
        <div style="font-size:13px;color:var(--ink-secondary);line-height:1.8;padding-top:8px">
          <p><b>4433法则</b>：经典选基规则。近1/2/3年+今年来收益排同类前1/4，近6月+近3月排前1/3。</p>
          <p><b>郑希6维评分</b>：基于基金经理郑希公开投资方法的6维度评估（景气方向、低位弹性、全球视野、流动性、周期拼接、业绩印证）。评分越高=越符合景气度投资框架。</p>
          <p><b>买入时机</b>：综合估值分位+趋势+RSI判断当前是否适合买入。</p>
          <p><b>投资方向</b>：根据基金持仓股票自动标注的行业/主题标签。</p>
        </div>
      </details>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from "vue"
import { api } from "../api"
import FundHoldings from "../components/FundHoldings.vue"
const allResults = ref<any[]>([]), filteredResults = ref<any[]>([]), loading = ref(false)
const scoreCode = ref(""), scoreResult = ref<any>(null), scoring = ref(false)
const selectedRegionFilter = ref<string | null>(null)
const watchlistCodes = ref<Set<string>>(new Set())
onMounted(async () => {
  fetchAll()
  try {
    const wl = await api.listWatch()
    wl.forEach((w: any) => watchlistCodes.value.add(w.code))
  } catch(e) {}
})
async function fetchAll() {
  loading.value = true
  const resp = await fetch(`/api/screener/4433-full?region=all`).then(r=>r.json())
  allResults.value = resp
  applyFilter()
  loading.value = false
}
function applyFilter() {
  if (selectedRegionFilter.value === null) {
    filteredResults.value = allResults.value
  } else if (selectedRegionFilter.value === "china") {
    filteredResults.value = allResults.value.filter((r:any) => ["cn","hk"].includes(r.region))
  } else if (selectedRegionFilter.value === "overseas") {
    filteredResults.value = allResults.value.filter((r:any) => ["us","jp","kr"].includes(r.region))
  }
}
function toggleRegionFilter(r: string) {
  selectedRegionFilter.value = selectedRegionFilter.value === r ? null : r
  applyFilter()
}
async function score() { scoring.value = true; scoreResult.value = await api.scoreFund(scoreCode.value); scoring.value = false }
async function addToWatch(f: any) {
  const code = f['基金代码'] || f.code
  await api.addWatch(code)
  watchlistCodes.value.add(code)
}
</script>
