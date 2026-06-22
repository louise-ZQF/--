<template>
  <div v-if="visible" style="margin-top:8px">
    <div v-if="loading" style="font-size:12px;color:var(--ink-secondary)">加载中...</div>
    <div v-else-if="error" style="color:var(--red);font-size:12px">{{ error }}</div>
    <div v-else-if="data">
      <div style="display:flex;gap:4px;height:8px;border-radius:4px;overflow:hidden;margin-bottom:4px">
        <div v-for="r in regionBars" :key="r.market"
          :style="{width:r.pct+'%', backgroundColor:r.color, minWidth:r.pct>0?'2px':'0'}"></div>
      </div>
      <div style="display:flex;gap:12px;font-size:11px;color:var(--ink-secondary);margin-bottom:8px">
        <span v-for="r in regionBars" :key="r.market">
          <span :style="{color:r.color,fontWeight:600}">&#9679;</span> {{ r.market }} {{ r.pct }}%
        </span>
      </div>
      <table style="width:100%;font-size:11px;border-collapse:collapse">
        <thead><tr style="color:var(--ink-secondary)">
          <th style="text-align:left;padding:2px 4px">名称</th>
          <th style="text-align:right;padding:2px 4px">占比</th>
          <th style="text-align:center;padding:2px 4px">市场</th>
        </tr></thead>
        <tbody>
          <tr v-for="h in data.top_holdings" :key="h.code">
            <td style="padding:2px 4px">{{ h.name }}</td>
            <td style="text-align:right;padding:2px 4px">{{ h.pct }}%</td>
            <td style="text-align:center;padding:2px 4px">
              <span class="badge" :style="{fontSize:'9px',padding:'1px 4px'}">{{ h.market }}</span>
            </td>
          </tr>
        </tbody>
      </table>
      <div style="font-size:10px;color:var(--ink-secondary);margin-top:4px">{{ data.disclaimer }}</div>
    </div>
  </div>
  <button v-else class="btn" @click="load" style="font-size:11px;padding:2px 8px">查看持仓</button>
</template>

<script setup lang="ts">
import { ref, computed } from "vue"
import { api } from "../api"

const props = defineProps<{ code: string }>()
const visible = ref(false)
const loading = ref(false)
const data = ref<any>(null)
const error = ref("")

const regionColors: Record<string,string> = {
  "A股":"#ef4444", "港股":"#10b981", "美股":"#3b82f6",
  "日本":"#f59e0b", "越南":"#8b5cf6", "印度":"#f97316",
  "德国":"#06b6d4", "其他":"#6b7280"
}
const regionBars = computed(() => {
  if (!data.value?.region_allocation) return []
  return Object.entries(data.value.region_allocation)
    .filter(([_,v]) => (v as number) > 0)
    .map(([k,v]) => ({ market: k, pct: v as number, color: regionColors[k] || "#6b7280" }))
})

async function load() {
  visible.value = true
  loading.value = true
  error.value = ""
  try {
    data.value = await api.fundHoldings(props.code)
  } catch(e: any) {
    error.value = "加载失败: " + (e?.message || e)
  }
  loading.value = false
}
</script>
