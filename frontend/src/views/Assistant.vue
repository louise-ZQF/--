<template>
  <div class="page">
    <h1 class="page-title">🤖 AI 助手</h1>
    <p class="page-subtitle">基于真实基金数据 · DeepSeek 驱动</p>

    <div class="card">
      <div style="display:flex;gap:10px;margin-bottom:12px">
        <input v-model="question" placeholder="输入你的问题…" style="flex:1" @keyup.enter="ask">
        <input v-model="qcode" placeholder="基金代码(可选)" style="width:140px">
        <button class="btn btn-primary" @click="ask" :disabled="loading">{{ loading ? '思考中…' : '发送' }}</button>
      </div>

      <div v-if="loading" class="loading">AI 思考中…</div>

      <div v-if="chat.length" style="margin-top:16px">
        <div v-for="(m,i) in chat" :key="i" style="margin-bottom:16px">
          <div style="font-weight:700;margin-bottom:4px;color:var(--brand)">{{ m.role === 'user' ? '🙋 你' : '🤖 AI' }}</div>
          <div style="background:#f9fafb;padding:12px 16px;border-radius:8px;white-space:pre-wrap;font-size:13px;line-height:1.7">{{ m.content }}</div>
        </div>
      </div>
    </div>

    <div class="card" v-if="!chat.length">
      <div class="empty-state"><div class="icon">🤖</div><div class="title">AI 基金研究助手</div><div class="desc">问我关于基金分析、定投策略、市场指标的任何问题</div></div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref } from "vue"
import { api } from "../api"
const question = ref(""), qcode = ref(""), chat = ref<any[]>([]), loading = ref(false)
async function ask() {
  if (!question.value) return
  chat.value.push({ role: "user", content: question.value })
  loading.value = true
  const resp = await api.ask(question.value, qcode.value || undefined)
  chat.value.push({ role: "assistant", content: resp.answer || "未获取到回答" })
  question.value = ""; loading.value = false
}
</script>
