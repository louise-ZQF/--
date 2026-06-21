<template>
  <div class="page">
    <h1 class="page-title">🔍 基金筛选</h1>
    <p class="page-subtitle">4433法则选基 · 经理风格评分</p>

    <div class="card">
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
        <thead><tr><th>代码</th><th>简称</th><th>近1年</th><th>近2年</th><th>近3年</th><th>近6月</th><th>近3月</th></tr></thead>
        <tbody>
          <tr v-for="f in results.slice(0,30)" :key="f['基金代码']||f.code">
            <td>{{ f['基金代码']||f.code }}</td>
            <td>{{ f['基金简称']||f.name }}</td>
            <td :style="{color:parseFloat(f.y1)>0?'var(--green)':'var(--red)'}">{{ f.y1 }}%</td>
            <td :style="{color:parseFloat(f.y2)>0?'var(--green)':'var(--red)'}">{{ f.y2 }}%</td>
            <td :style="{color:parseFloat(f.y3)>0?'var(--green)':'var(--red)'}">{{ f.y3 }}%</td>
            <td>{{ f.m6 }}%</td><td>{{ f.m3 }}%</td>
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
async function screen() { loading.value = true; results.value = await api.screen4433(); loading.value = false }
async function score() { scoring.value = true; scoreResult.value = await api.scoreFund(scoreCode.value); scoring.value = false }
</script>
