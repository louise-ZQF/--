<template>
  <div class="page">
    <h1 class="page-title">自选监控</h1>
    <p class="page-subtitle">智能买点提醒 · 估值/回撤/RSI/趋势 四维判断</p>

    <div class="card">
      <div style="display:flex;gap:10px">
        <input v-model="newCode" placeholder="基金代码, 如 001513" style="flex:1;max-width:200px">
        <button class="btn btn-primary" @click="add">添加自选</button>
        <button class="btn" @click="checkSignals" :disabled="loading">
          {{ loading ? '检查中…' : '刷新信号' }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading">检查买入信号…</div>

    <div v-if="signals.length">
      <div class="card" v-for="s in signals" :key="s.code">
        <div class="signal-row" :class="s.can_buy ? 'signal-buy' : 'signal-wait'" :style="{'border-left': '3px solid ' + (s.can_buy ? 'var(--green)' : 'var(--amber)')}">
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
            <span :style="{color: check.pass ? 'var(--green)' : 'var(--red)'}">●</span>
            <span style="flex:1">{{ label }}</span>
            <span :style="{color: check.pass ? 'var(--green)' : 'var(--red)'}">{{ check.value }}</span>
          </div>
        </div>

        <!-- 短期行情与持仓分析 -->
        <details v-if="s.perf || s.holdings_summary" style="margin-top:10px;padding-top:10px;border-top:1px solid var(--line);cursor:pointer">
          <summary style="font-size:12px;color:var(--muted);font-weight:500">短期行情与持仓分析</summary>
          <div style="padding-top:8px;font-size:12px">
            <div v-if="s.perf" style="display:flex;flex-wrap:wrap;gap:6px 12px;margin-bottom:10px">
              <span>排名: <b :style="{color: s.perf.rank / s.perf.total_funds <= 0.1 ? 'var(--green)' : s.perf.rank / s.perf.total_funds > 0.5 ? 'var(--red)' : 'var(--ink-secondary)'}">{{ s.perf.rank }}/{{ s.perf.total_funds }}</b></span>
              <span>日涨幅: <b :style="{color: s.perf.daily >= 0 ? 'var(--green)' : 'var(--red)'}">{{ s.perf.daily }}%</b></span>
              <span>近1周: <b :style="{color: s.perf.week_1 >= 0 ? 'var(--green)' : 'var(--red)'}">{{ s.perf.week_1 }}%</b></span>
              <span>近1月: <b :style="{color: s.perf.month_1 >= 0 ? 'var(--green)' : 'var(--red)'}">{{ s.perf.month_1 }}%</b></span>
              <span>净值: <b>{{ s.perf.nav }}</b></span>
            </div>
            <div v-if="s.holdings_summary?.region_distribution" style="margin-bottom:10px">
              <div style="display:flex;gap:4px;height:8px;border-radius:4px;overflow:hidden;margin-bottom:4px">
                <div v-for="reg in s.holdings_summary.region_distribution" :key="reg.market"
                  :style="{width: reg.percent + '%', backgroundColor: reg.market === 'A股' ? '#ef4444' : reg.market === '港股' ? '#10b981' : reg.market === '美股' ? '#3b82f6' : '#6b7280', minWidth: reg.percent > 0 ? '2px' : '0'}">
                </div>
              </div>
              <div style="display:flex;flex-wrap:wrap;gap:4px 12px">
                <span v-for="reg in s.holdings_summary.region_distribution" :key="reg.market" style="font-size:11px;color:var(--ink-secondary)">
                  <span :style="{color: reg.market === 'A股' ? '#ef4444' : reg.market === '港股' ? '#10b981' : reg.market === '美股' ? '#3b82f6' : '#6b7280', fontWeight:600}">●</span>
                  {{ reg.market }} {{ reg.percent }}%
                </span>
              </div>
            </div>
            <div v-if="s.holdings_summary?.top_holdings?.length">
              <div style="font-size:11px;color:var(--ink-secondary);margin-bottom:4px">前5大持仓</div>
              <div v-for="(h, i) in s.holdings_summary.top_holdings.slice(0,5)" :key="i" style="display:flex;align-items:center;gap:8px;padding:2px 0">
                <span style="flex:1;font-size:12px">{{ h.name }}</span>
                <span style="font-size:11px;color:var(--ink-secondary)">{{ h.percent }}%</span>
                <span v-if="h.market" class="badge" :style="{fontSize:'9px',padding:'1px 5px',backgroundColor: h.market === 'A股' ? '#fef2f2' : h.market === '港股' ? '#ecfdf5' : h.market === '美股' ? '#eff6ff' : '#f3f4f6', color: h.market === 'A股' ? '#dc2626' : h.market === '港股' ? '#059669' : h.market === '美股' ? '#2563eb' : '#4b5563'}">{{ h.market }}</span>
              </div>
            </div>
          </div>
        </details>

        <!-- FundCrawler enriched overview -->
        <details v-if="s.overview?.fund_type || s.manager?.manager_name" style="margin-top:10px;padding-top:10px;border-top:1px solid var(--line);cursor:pointer">
          <summary style="font-size:12px;color:var(--muted);font-weight:500">基金概况</summary>
          <div style="font-size:12px;color:var(--ink-secondary);display:grid;grid-template-columns:1fr 1fr;gap:4px 16px;padding-top:8px">
            <template v-if="s.overview?.fund_type"><span>类型</span><b>{{ s.overview.fund_type }}</b></template>
            <template v-if="s.overview?.fund_size"><span>规模</span><b>{{ s.overview.fund_size }}亿</b></template>
            <template v-if="s.overview?.fund_company"><span>基金公司</span><b>{{ s.overview.fund_company }}</b></template>
            <template v-if="s.overview?.fund_value"><span>单位净值</span><b>{{ s.overview.fund_value }}</b></template>
            <template v-if="s.overview?.management_fee"><span>管理费率</span><b>{{ s.overview.management_fee }}</b></template>
            <template v-if="s.overview?.custody_fee"><span>托管费率</span><b>{{ s.overview.custody_fee }}</b></template>
            <template v-if="s.manager?.manager_name"><span>基金经理</span><b>{{ s.manager.manager_name }}（{{ s.manager.appointment_date }}上任）</b></template>
            <template v-if="s.risk?.stddev_3y"><span>近3年波动</span><b>{{ s.risk.stddev_3y }}</b></template>
            <template v-if="s.risk?.sharpe_3y"><span>近3年夏普</span><b>{{ s.risk.sharpe_3y }}</b></template>
          </div>
        </details>
      </div>
    </div>

    <div class="card" v-if="!signals.length && !loading && watchlist.length">
      <div class="empty-state">
        <div class="title">点击"刷新信号"查看买点</div>
      </div>
    </div>

    <div class="card" v-if="!watchlist.length && !loading">
      <div class="empty-state">
        <div class="title">还没有自选基金</div>
        <div class="desc">添加你关注的基金，智能监控买入时机</div>
      </div>
    </div>

    <div class="card" style="margin-top:20px">
      <details style="cursor:pointer">
        <summary style="font-weight:600;font-size:15px;margin-bottom:12px">术语解释</summary>
        <div style="font-size:13px;color:var(--ink-secondary);line-height:1.8;padding-top:8px">
          <p><b>估值偏低(分位&lt;35%)</b>：当前净值处于近3年较低位置，买入性价比相对较高。</p>
          <p><b>已回调(距高点&lt;-10%)</b>：基金净值从近1年最高点回落超过10%，出现像样回调。</p>
          <p><b>未超买(RSI&lt;60)</b>：短期未出现过热，买入后短期回调风险相对可控。</p>
          <p><b>趋势非向下</b>：中期均线未持续走低，避免在下跌趋势中接飞刀。</p>
          <p><b>四维判断</b>：四项条件全部满足=可考虑买入。任一不满足=暂不建议，等条件改善。</p>
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
