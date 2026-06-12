<script setup lang="ts">
import { ref, onMounted, computed, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getStatsOverview, getStatsByClass, getStatsByStudent, listRecords } from '@/api/essay'
import type { RecordSummary } from '@/api/essay'

const overview = ref({ total_records: 0, avg_score: 0, max_score: 0 })
const classStats = ref<Array<{ class_id: string; record_count: number; avg_score: number }>>([])
const students = ref<RecordSummary[]>([])
const selectedStudentId = ref('')
const studentTrend = ref<Array<{ total_score: number; subject: string; created_at: string }>>([])

const barChartRef = ref<HTMLDivElement>()
const lineChartRef = ref<HTMLDivElement>()
let barChart: echarts.ECharts | null = null
let lineChart: echarts.ECharts | null = null

async function loadOverview() {
  try {
    overview.value = await getStatsOverview()
    classStats.value = await getStatsByClass()
  } catch { /* ignore */ }
}

async function loadStudents() {
  try {
    const data = await listRecords(200)
    // 去重学生列表
    const seen = new Set<string>()
    students.value = data.items.filter((r) => {
      if (!r.student_id || seen.has(r.student_id)) return false
      seen.add(r.student_id)
      return true
    })
  } catch { /* ignore */ }
}

async function selectStudent(studentId: string) {
  selectedStudentId.value = studentId
  try {
    studentTrend.value = await getStatsByStudent(studentId)
    await nextTick()
    renderLineChart()
  } catch { /* ignore */ }
}

function renderBarChart() {
  if (!barChartRef.value) return
  barChart?.dispose()
  barChart = echarts.init(barChartRef.value)
  barChart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: classStats.value.map((c) => c.class_id || '未知'),
      axisLabel: { rotate: 30 },
    },
    yAxis: { type: 'value', name: '平均分', max: 100 },
    series: [{
      type: 'bar',
      data: classStats.value.map((c) => c.avg_score),
      itemStyle: { color: '#409eff', borderRadius: [4, 4, 0, 0] },
      label: { show: true, position: 'top', fontSize: 12 },
    }],
  })
}

function renderLineChart() {
  if (!lineChartRef.value) return
  lineChart?.dispose()
  lineChart = echarts.init(lineChartRef.value)
  lineChart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: studentTrend.value.map((s) => s.created_at?.slice(0, 10) || ''),
    },
    yAxis: { type: 'value', name: '总分', max: 100, min: 0 },
    series: [{
      type: 'line',
      data: studentTrend.value.map((s) => s.total_score),
      smooth: true,
      itemStyle: { color: '#67c23a' },
      areaStyle: { color: 'rgba(103, 194, 58, 0.15)' },
      markLine: {
        data: [{ type: 'average', name: '平均' }],
        silent: true,
      },
    }],
  })
}

onMounted(async () => {
  await Promise.all([loadOverview(), loadStudents()])
  await nextTick()
  renderBarChart()
})
</script>

<template>
  <div class="dashboard-page">
    <h2>成绩看板</h2>

    <!-- 概览卡片 -->
    <div class="overview-cards">
      <el-card>
        <el-statistic title="批改总数" :value="overview.total_records" />
      </el-card>
      <el-card>
        <el-statistic title="平均分" :value="overview.avg_score" suffix="/ 100" :precision="1" />
      </el-card>
      <el-card>
        <el-statistic title="最高分" :value="overview.max_score" suffix="/ 100" />
      </el-card>
    </div>

    <!-- 班级统计 -->
    <el-card style="margin-top: 20px;">
      <template #header>班级平均分对比</template>
      <div ref="barChartRef" style="height: 300px;" />

      <el-table v-if="classStats.length" :data="classStats" style="margin-top: 16px;">
        <el-table-column prop="class_id" label="班级" />
        <el-table-column prop="record_count" label="批改数" width="100" />
        <el-table-column label="平均分" width="100">
          <template #default="{ row }">{{ row.avg_score }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 学生趋势 -->
    <el-card style="margin-top: 20px;">
      <template #header>学生成绩趋势</template>
      <el-select
        v-model="selectedStudentId"
        placeholder="选择学生"
        clearable
        style="width: 240px;"
        @change="selectStudent"
      >
        <el-option
          v-for="s in students"
          :key="s.student_id"
          :label="`${s.student_name || s.student_id} (${s.student_id})`"
          :value="s.student_id"
        />
      </el-select>

      <div v-if="studentTrend.length" ref="lineChartRef" style="height: 300px; margin-top: 16px;" />
      <el-empty v-else-if="selectedStudentId" description="暂无成绩数据" :image-size="60" />
    </el-card>
  </div>
</template>

<style scoped>
.dashboard-page {
  max-width: 1000px;
  margin: 0 auto;
}

h2 {
  font-size: 24px;
  margin-bottom: 20px;
}

.overview-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
</style>
