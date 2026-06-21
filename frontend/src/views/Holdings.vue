<template>
  <div class="page">
    <h1 class="page-title">我的持仓</h1>
    <p class="page-subtitle">导入持仓 · 分析投资方向 · 被动/主动配置建议</p>

    <!-- Import -->
    <div class="card">
      <p style="font-size:13px;color:var(--ink-secondary);margin-bottom:12px">每行一个基金代码，无需输入金额</p>
      <textarea v-model="batchText" rows="4" placeholder="001513&#10;270042&#10;050025&#10;110020" style="width:100%;font-family:monospace;font-size:14px"></textarea>
      <div style="display:flex;gap:10px;margin-top:12px">
        <button class="btn btn-primary" @click="batchImport" :disabled="loading">
          {{ loading ? '分析中…' : '导入并分析' }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading">分析中…</div>

    <div v-if="importError" class="card" style="background:#fef2f2;border:1px solid #fecaca;color:#dc2626;font-size:13px;padding:12px">
      {{ importError }}
    </div>
    <div v-if="importSuccess" class="card" style="background:#f0fdf4;border:1px solid #bbf7d0;color:#16a34a;font-size:13px;padding:12px">
      {{ importSuccess }}
    </div>

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
          <div v-if="f.error" style="color:#dc2626;font-size:13px;padding:6px 0;background:#fef2f2;border-radius:4px;margin-bottom:8px">⚠ {{ f.error }}</div>
          <template v-else>
          <div v-if="f.perf" style="display:flex;flex-wrap:wrap;gap:4px 12px;font-size:11px;color:var(--ink-secondary);margin-bottom:8px">
            <span>日涨幅: <b :style="{color:f.perf.daily>=0?'var(--green)':'var(--red)'}">{{ f.perf.daily }}%</b></span>
            <span>近1周: <b :style="{color:f.perf.week_1>=0?'var(--green)':'var(--red)'}">{{ f.perf.week_1 }}%</b></span>
            <span>近1月: <b :style="{color:f.perf.month_1>=0?'var(--green)':'var(--red)'}">{{ f.perf.month_1 }}%</b></span>
            <span>排名: <b :style="{color:f.perf.rank_pct<=20?'var(--green)':f.perf.rank_pct<=50?'var(--amber)':'var(--red)'}">{{ f.perf.category }} {{ f.perf.rank }}/{{ f.perf.total_funds }} (前{{ f.perf.rank_pct }}%)</b></span>
          </div>
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
          <div v-if="f.risk?.sharpe_ratio" style="display:flex;gap:16px;margin-top:6px;font-size:11px;color:var(--ink-secondary)">
            <span>夏普 {{ f.risk.sharpe_ratio?.toFixed(2) }}</span>
            <span>波动率 {{ (f.risk.annual_volatility*100)?.toFixed(1) }}%</span>
            <span>Calmar {{ f.risk.calmar_ratio?.toFixed(2) }}</span>
          </div>
        </template>
      </div>
    </div>
  </div>

    <!-- Empty -->
    <div class="card" v-if="!portfolio.funds?.length && !loading">
      <div class="empty-state"><div class="title">导入你的持仓</div><div class="desc">粘贴基金代码，智能分析投资方向与配置建议</div></div>
    </div>

    <!-- New Analysis Dimensions -->
    <div v-if="portfolio.concentration || portfolio.correlation || portfolio.suggestions?.length" style="margin-top:16px">

      <!-- Concentration + Valuation -->
      <div v-if="portfolio.concentration" class="card">
        <h3 style="font-size:14px;font-weight:600;margin-bottom:12px">集中度分析</h3>
        <div style="display:flex;gap:24px;flex-wrap:wrap">
          <div>
            <span style="font-size:12px;color:var(--ink-secondary)">前3大持仓占比</span>
            <div style="font-size:24px;font-weight:700" :style="{color: portfolio.concentration.top3_pct>60?'var(--red)':portfolio.concentration.top3_pct>30?'var(--amber)':'var(--green)'}">{{ portfolio.concentration.top3_pct }}%</div>
          </div>
          <div>
            <span style="font-size:12px;color:var(--ink-secondary)">前5大持仓占比</span>
            <div style="font-size:24px;font-weight:700">{{ portfolio.concentration.top5_pct }}%</div>
          </div>
          <div>
            <span style="font-size:12px;color:var(--ink-secondary)">集中度等级</span>
            <div style="font-size:16px;font-weight:600;margin-top:4px">{{ portfolio.concentration.level }}</div>
          </div>
        </div>
        <div v-if="portfolio.concentration.overlap_warning" class="advice-box advice-wait" style="margin-top:10px">
          {{ portfolio.concentration.overlap_warning }}
        </div>
      </div>

      <!-- Valuation Health -->
      <div v-if="portfolio.valuation_health" class="card" style="margin-top:12px">
        <h3 style="font-size:14px;font-weight:600;margin-bottom:8px">估值健康度</h3>
        <div style="display:flex;align-items:center;gap:12px">
          <div style="font-size:28px;font-weight:700" :style="{color: portfolio.valuation_health.avg_percentile<0.4?'var(--green)':portfolio.valuation_health.avg_percentile<0.6?'var(--amber)':'var(--red)'}">{{ (portfolio.valuation_health.avg_percentile*100).toFixed(0) }}%</div>
          <div>
            <div style="font-size:14px;font-weight:600">{{ portfolio.valuation_health.level }}</div>
            <div style="font-size:12px;color:var(--ink-secondary)">{{ portfolio.valuation_health.advice }}</div>
          </div>
        </div>
      </div>

      <!-- Risk Metrics -->
      <div v-if="portfolio.risk_metrics" class="card" style="margin-top:12px">
        <h3 style="font-size:14px;font-weight:600;margin-bottom:8px">组合风险指标</h3>
        <div style="display:flex;gap:24px;flex-wrap:wrap;font-size:13px">
          <div><span style="color:var(--ink-secondary)">年化波动率 </span><b>{{ (portfolio.risk_metrics.portfolio_volatility*100).toFixed(1) }}%</b></div>
          <div><span style="color:var(--ink-secondary)">夏普比率 </span><b :style="{color:portfolio.risk_metrics.portfolio_sharpe>0?'var(--green)':'var(--red)'}">{{ portfolio.risk_metrics.portfolio_sharpe?.toFixed(2) }}</b></div>
          <div><span style="color:var(--ink-secondary)">最大回撤 </span><b :style="{color:portfolio.risk_metrics.portfolio_max_drawdown<-0.3?'var(--red)':portfolio.risk_metrics.portfolio_max_drawdown<-0.15?'var(--amber)':'var(--green)'}">{{ (portfolio.risk_metrics.portfolio_max_drawdown*100).toFixed(1) }}%</b></div>
        </div>
      </div>

      <!-- Correlation -->
      <div v-if="portfolio.correlation?.high_pairs?.length" class="card" style="margin-top:12px">
        <h3 style="font-size:14px;font-weight:600;margin-bottom:8px">相关性风险</h3>
        <div style="font-size:12px;color:var(--ink-secondary);margin-bottom:8px">平均相关性 {{ portfolio.correlation.avg_correlation?.toFixed(2) }}</div>
        <div v-for="p in portfolio.correlation.high_pairs" :key="p.fund_a+p.fund_b" class="advice-box advice-wait" style="margin-bottom:6px">
          {{ p.warning }}（{{ p.correlation }}）
        </div>
      </div>

      <!-- Suggestions -->
      <div v-if="portfolio.suggestions?.length" class="card" style="margin-top:12px">
        <h3 style="font-size:14px;font-weight:600;margin-bottom:10px">改进建议</h3>
        <div v-for="(s,i) in portfolio.suggestions" :key="i" style="display:flex;gap:8px;padding:6px 0;font-size:13px;border-bottom:1px solid var(--line)">
          <span style="color:var(--brand);font-weight:600;min-width:20px">{{ i+1 }}.</span>
          <span>{{ s }}</span>
        </div>
      </div>
    </div>

    <div class="card" style="margin-top:20px">
      <details style="cursor:pointer">
        <summary style="font-weight:600;font-size:15px;margin-bottom:12px">术语解释</summary>
        <div style="font-size:13px;color:var(--ink-secondary);line-height:1.8;padding-top:8px">
          <p><b>估值分位</b>：当前净值在近3年历史中的位置。分位越低=越便宜，定投性价比越高。分位100%=历史最高点。</p>
          <p><b>RSI</b>：相对强弱指标，0-100。RSI&gt;70表示短期过热（超买），RSI&lt;30表示短期过冷（超卖）。</p>
          <p><b>趋势</b>：60日均线方向。向上=中期趋势向好，向下=中期趋势偏弱。</p>
          <p><b>被动指数基金</b>：跟踪某个指数（如纳斯达克100、沪深300），费率低、透明度高。</p>
          <p><b>主动管理基金</b>：由基金经理主动选股，目标是战胜基准指数。</p>
          <p><b>被动/主动评分</b>：基于当前市场估值，判断被动指数和主动基金哪个更适合配置。高分=被动更优，低分=主动更优。</p>
          <p><b>投资方向</b>：根据基金前十大持仓股票，自动标注基金主要投资的行业/主题。</p>
        </div>
      </details>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue"
import { api } from "../api"

const batchText = ref("")
const portfolio = ref<any>({})
const loading = ref(false)
const importError = ref("")
const importSuccess = ref("")

async function batchImport() {
  importError.value = ""
  importSuccess.value = ""
  const codes = batchText.value.trim().split(/[\n,，\s]+/).filter(c => c.length >= 5)
  if (!codes.length) {
    importError.value = "未检测到有效基金代码（需要5-6位数字）"
    return
  }
  loading.value = true
  try {
    const items = codes.map(c => ({ code: c.trim(), name: "" }))
    // Step 1: 快速存库
    const saveResult = await api.batchImport(items)
    importSuccess.value = "已保存 " + saveResult.count + " 只基金，正在分析..."

    // Step 2: 分析（可能较慢，但后端已并行优化）
    portfolio.value = await api.analyzeHoldings(items)

    // 检查是否有部分基金失败
    const errors = portfolio.value.funds?.filter((f: any) => f.error)
    if (errors?.length) {
      importError.value = errors.length + " 只基金分析失败: " + errors.map((e: any) => e.code + " " + e.error).join(", ")
    }

    importSuccess.value = "已导入 " + saveResult.count + " 只基金，分析完成"
    batchText.value = ""
  } catch (e: any) {
    importError.value = "导入失败: " + (e?.message || e?.toString?.() || "未知错误")
    console.error("批量导入失败", e)
  }
  loading.value = false
}
</script>
