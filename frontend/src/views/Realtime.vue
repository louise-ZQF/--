<template>
  <div class="page">
    <h1 class="page-title">实时估值 <span class="dot" :class="{active:isTrading}"></span></h1>
    <p class="page-subtitle">{{ isTrading?'盘中估算 · 每60秒自动刷新':'已收盘 · 下一交易日9:30恢复' }}</p>
    <div style="display:flex;gap:8px;margin-bottom:20px">
      <button v-for="f in filters" :key="f.k" class="btn" :class="f.k===current?'btn-primary':''" @click="switchF(f.k)">{{ f.l }}</button>
      <button class="btn" @click="fetch" :disabled="loading" style="margin-left:auto">&#x21bb; 刷新</button>
    </div>
    <div v-if="loading && !funds.length" class="loading">加载中…</div>
    <div v-if="!isTrading && funds.length" class="card" style="font-size:12px;color:var(--ink-secondary);background:#fafafa">非交易时间，显示最近估值快照</div>
    <div v-if="funds.length" class="card" style="padding:0;overflow:hidden">
      <table>
        <thead><tr>
          <th>代码</th><th>名称</th><th style="text-align:right">估算涨幅</th><th style="text-align:right">估算净值</th><th>估值时间</th><th>标签</th>
        </tr></thead>
        <tbody>
          <tr v-for="f in funds" :key="f.code">
            <td style="font-family:monospace;font-size:12px;color:var(--ink-secondary)">{{ f.code }}</td>
            <td style="font-weight:500">{{ f.name||'-' }}</td>
            <td style="text-align:right">
              <b v-if="!f.error" :style="{color:parseFloat(f.estimated_change)>=0?'#ef4444':'#10b981'}">{{ parseFloat(f.estimated_change)>=0?'+':'' }}{{ f.estimated_change }}%</b>
              <span v-else style="color:#9ca3af;font-size:12px">{{ f.error }}</span>
            </td>
            <td style="text-align:right;font-family:monospace;font-size:13px">{{ f.estimated_nav||'-' }}</td>
            <td style="font-size:12px;color:var(--ink-secondary)">{{ f.update_time||'-' }}</td>
            <td><span v-for="t in f.tags" :key="t" class="badge" :style="{fontSize:'10px',marginRight:'4px',backgroundColor:t==='持有'?'#dcfce7':'#dbeafe',color:t==='持有'?'#16a34a':'#2563eb'}">{{ t }}</span></td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-if="!funds.length && !loading" class="card">
      <div class="empty-state"><div class="title">暂无持仓或自选基金</div><div class="desc">请先在「持仓」或「自选」页面添加基金</div></div>
    </div>
    <div style="text-align:center;font-size:12px;color:var(--ink-secondary);padding:16px 0">盘中估算，盘后以官方净值为准</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue"
import { api } from "../api"

const filters = [{k:"all",l:"全部"},{k:"holding",l:"持有"},{k:"watch",l:"自选"}]
const current = ref("all")
const funds = ref<any[]>([])
const isTrading = ref(false)
const loading = ref(false)
let timer: any = null

async function fetch() {
  loading.value = true
  try {
    const d = await api.realtime(current.value)
    funds.value = d.funds||[]
    isTrading.value = d.is_trading
  } catch(e: any) { console.error(e) }
  loading.value = false
}
function switchF(k: string) { current.value = k; fetch() }

onMounted(() => { fetch(); timer = setInterval(fetch, 60000) })
onUnmounted(() => { if(timer) clearInterval(timer) })
</script>

<style scoped>
.dot { display:inline-block;width:10px;height:10px;border-radius:50%;background:#9ca3af;vertical-align:middle }
.dot.active { background:#10b981;box-shadow:0 0 0 3px rgba(16,185,129,.3);animation:pulse 2s infinite }
@keyframes pulse { 0%,100%{box-shadow:0 0 0 3px rgba(16,185,129,.3)} 50%{box-shadow:0 0 0 8px rgba(16,185,129,.1)} }
</style>
