<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import * as echarts from 'echarts'
import type { ScoresData } from '@/types/grading'
import { dimensionLabelMap } from '@/types/grading'

const props = defineProps<{
  scores: ScoresData | null
  totalScore: number
  subject?: string
}>()

const chartRef = ref<HTMLDivElement>()
let chartInstance: echarts.ECharts | null = null

// 按科目的维度标签映射
const dimensionLabelBySubject: Record<string, Record<string, string>> = {
  en: { neatness: '卷面整洁', content: '内容要点', language: '语言质量', structure: '篇章结构' },
  cn: { neatness: '内容立意', content: '语言表达', language: '篇章结构', structure: '书写规范' },
}

const currentLabels = computed(() => {
  const subj = props.subject || 'en'
  return dimensionLabelBySubject[subj] || dimensionLabelBySubject.en
})

const dimensions = computed(() => {
  if (!props.scores) return []
  const labels = currentLabels.value
  return [
    { name: labels.neatness, score: props.scores.neatness.score, max: 25 },
    { name: labels.content, score: props.scores.content.score, max: 25 },
    { name: labels.language, score: props.scores.language.score, max: 25 },
    { name: labels.structure, score: props.scores.structure.score, max: 25 },
  ]
})

function renderChart() {
  if (!chartRef.value) return

  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }

  const dims = dimensions.value

  chartInstance.setOption({
    radar: {
      center: ['50%', '55%'],
      radius: '65%',
      indicator: dims.map((d) => ({ name: d.name, max: d.max })),
      axisName: {
        fontSize: 13,
      },
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: dims.map((d) => d.score),
            name: '得分',
            areaStyle: {
              color: 'rgba(64, 158, 255, 0.2)',
            },
            lineStyle: {
              color: '#409eff',
              width: 2,
            },
            itemStyle: {
              color: '#409eff',
            },
          },
        ],
      },
    ],
  })
}

onMounted(() => {
  renderChart()
})

watch(() => props.scores, () => {
  setTimeout(renderChart, 100)
}, { deep: true })
</script>

<template>
  <el-card>
    <template #header>
      <span class="card-title">作文评分</span>
    </template>

    <div v-if="scores" class="score-board">
      <!-- 综合得分 -->
      <div class="total-score-section">
        <el-statistic
          :value="totalScore"
          :max="100"
          title="综合得分"
        >
          <template #suffix>/ 100</template>
        </el-statistic>
      </div>

      <!-- 雷达图 -->
      <div class="radar-section" ref="chartRef" />

      <!-- 各维度详情 -->
      <div class="dimensions-section">
        <div
          v-for="(dim, key) in scores"
          :key="key"
          class="dimension-item"
        >
          <div class="dim-header">
            <span class="dim-label">{{ currentLabels[key] || key }}</span>
            <span class="dim-score">{{ dim.score }} / 25</span>
          </div>
          <el-progress
            :percentage="(dim.score / 25) * 100"
            :stroke-width="8"
            :color="dim.score >= 20 ? '#67c23a' : dim.score >= 15 ? '#409eff' : dim.score >= 10 ? '#e6a23c' : '#f56c6c'"
          />
          <p class="dim-comment">{{ dim.comment }}</p>
        </div>
      </div>
    </div>

    <el-empty v-else description="暂无评分数据" :image-size="60" />
  </el-card>
</template>

<style scoped>
.card-title {
  font-size: 16px;
  font-weight: 600;
}

.score-board {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.total-score-section {
  text-align: center;
  padding: 16px;
  background: linear-gradient(135deg, #409eff10, #409eff05);
  border-radius: 12px;
}

.radar-section {
  height: 320px;
}

.dimensions-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.dimension-item {
  padding: 12px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
}

.dim-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.dim-label {
  font-weight: 500;
  font-size: 14px;
}

.dim-score {
  font-size: 18px;
  font-weight: 700;
  color: #409eff;
}

.dim-comment {
  margin-top: 6px;
  font-size: 13px;
  color: #888;
}
</style>
