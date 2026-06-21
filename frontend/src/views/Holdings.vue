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

    <!-- Batch import -->
    <div class="card">
      <h3 style="margin-bottom:8px">📥 批量导入</h3>
      <p style="font-size:12px;color:var(--muted);margin-bottom:8px">每行一只：<code>代码 成本净值 每日定投额</code>，如 <code>001513 3.5 100</code></p>
      <textarea v-model="batchText" rows="4" placeholder="001513 3.5 100&#10;270042 1.8 50&#10;050025 2.1 80" style="width:100%;font-family:monospace;font-size:13px"></textarea>
      <button class="btn btn-primary" @click="batchImport" :disabled="loading" style="margin-top:8px">
        {{ loading ? '导入中…' : '📥 批量导入并分析' }}
      </button>
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
          <div class="label">{{ r.name || r.code }} <span style="font-size:11px;color:var(--ink-secondary);margin-left:8px">{{ r.code }}</span></div>
          <div class="value" :style="{color: r.return > 0 ? 'var(--green)' : 'var(--red)'}">
            {{ (r.return*100).toFixed(1) }}%
          </div>
          <div class="sub">净值 {{ r.current_nav }} · 回撤 {{ (r.max_drawdown*100).toFixed(1) }}%</div>
          <!-- DCA 建议卡片 -->
          <div class="advice-box" :class="r.dca_advice?.includes('加大') ? 'advice-buy' : r.dca_advice?.includes('暂停') ? 'advice-wait' : 'advice-info'" style="margin-top:10px">
            <div style="font-size:15px;font-weight:700">{{ r.dca_advice || '—' }}</div>
            <div style="font-size:12px;margin-top:4px">{{ r.dca_reason || '' }}</div>
          </div>
          <div style="display:flex;gap:12px;margin-top:8px;font-size:12px">
            <span>📊 估值分位: {{ (r.percentile*100).toFixed(0) }}%</span>
            <span>📈 趋势: {{ r.trend }}</span>
          </div>
        </div>
      </div>

      <!-- 仓位配比建议 (合并至此) -->
      <div class="card" v-if="results.length >= 2" style="margin-top:20px">
        <h3 style="font-size:17px;font-weight:600;margin-bottom:4px">⚖️ 仓位配比建议</h3>
        <p style="font-size:13px;color:var(--ink-secondary);margin-bottom:16px">基于当前持仓的最优权重分配</p>
        <div style="display:flex;gap:10px;align-items:center;margin-bottom:16px">
          <select v-model="optMethod" style="width:180px">
            <option value="max_sharpe">最大夏普比率</option>
            <option value="min_var">最小方差</option>
            <option value="risk_parity">风险平价</option>
          </select>
          <button class="btn btn-primary" @click="runOptimize" :disabled="optLoading">
            {{ optLoading ? '计算中…' : '🎯 计算最优配比' }}
          </button>
        </div>
        <div v-if="optResult && !optResult.error">
          <div class="stat-grid" style="margin-bottom:12px">
            <div class="stat-card">
              <div class="label">预期年化收益</div>
              <div class="value" style="color:var(--green);font-size:24px">{{ (optResult.expected_return*100).toFixed(2) }}%</div>
            </div>
            <div class="stat-card">
              <div class="label">预期波动</div>
              <div class="value" style="font-size:24px">{{ (optResult.expected_vol*100).toFixed(2) }}%</div>
            </div>
            <div class="stat-card">
              <div class="label">夏普比率</div>
              <div class="value" style="color:var(--brand);font-size:24px">{{ optResult.sharpe }}</div>
            </div>
          </div>
          <div v-for="(w, code) in optResult.weights" :key="code" style="display:flex;align-items:center;gap:12px;margin:8px 0">
            <span style="width:100px;font-size:13px;font-weight:500">{{ code }}</span>
            <div style="flex:1;height:20px;background:#f0f0f3;border-radius:10px;overflow:hidden">
              <div :style="{width:(w*100)+'%',height:'100%',background:'linear-gradient(90deg, #0071e3, #40a9ff)',borderRadius:'10px',transition:'width .6s cubic-bezier(0.25,0.1,0.25,1)'}"></div>
            </div>
            <span style="font-weight:600;width:50px;text-align:right;font-size:13px">{{ (w*100).toFixed(1) }}%</span>
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
const batchText = ref("")
const holdings = ref<any[]>([])
const results = ref<any[]>([])
const loading = ref(false)
const optMethod = ref("max_sharpe")
const optResult = ref<any>(null)
const optLoading = ref(false)

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

async function runOptimize() {
  const codes = results.value.map((r: any) => r.code).filter(Boolean)
  if (codes.length < 2) return
  optLoading.value = true
  optResult.value = await api.optimize(codes, optMethod.value)
  optLoading.value = false
}

async function batchImport() {
  const lines = batchText.value.trim().split("\n").filter(Boolean)
  const items = lines.map(line => {
    const parts = line.trim().split(/\s+/)
    return {
      code: parts[0] || "",
      cost: parseFloat(parts[1]) || 0,
      dca_daily: parseFloat(parts[2]) || 0,
      name: parts.slice(3).join(" ") || "",
    }
  }).filter(h => h.code)

  if (!items.length) return
  loading.value = true
  const resp = await fetch("/api/holdings/batch-import", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(items)
  }).then(r => r.json())
  results.value = resp
  holdings.value = await api.listHoldings()
  loading.value = false
  batchText.value = ""
}
</script>
