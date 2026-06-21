<template><div ref="el" style="width:100%;height:240px"></div></template>
<script setup lang="ts">
import * as echarts from "echarts"
import { onMounted, ref, watch } from "vue"
const props = defineProps<{ data: {date:string; value:number; cost?:number}[] }>()
const el = ref<HTMLDivElement>()
let chart: any
function render(){
  if(!el.value || !props.data.length) return
  chart ??= echarts.init(el.value)
  chart.setOption({
    grid: { top: 10, right: 10, bottom: 20, left: 50 },
    xAxis: { type:"category", data: props.data.map(d=>d.date), show: false },
    yAxis: { type:"value", scale: true, splitLine: { lineStyle: { color: "#f0f0f0" } } },
    series: [{
      type: "line", smooth: true, showSymbol: false,
      data: props.data.map(d=>d.value),
      lineStyle: { color: "#3b82f6", width: 2 },
      areaStyle: { color: "rgba(59,130,246,0.08)" }
    }]
  })
}
onMounted(render); watch(()=>props.data, render, {deep:true})
</script>
