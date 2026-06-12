<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getGradingRecord } from '@/api/essay'
import type { GradeResult } from '@/types/grading'
import ResultPanel from '@/components/ResultPanel.vue'

const route = useRoute()
const router = useRouter()
const batchId = route.params.batchId as string
const recordId = route.params.recordId as string

const result = ref<GradeResult | null>(null)
const loading = ref(true)

async function fetchResult() {
  try {
    const data = await getGradingRecord(recordId)
    result.value = {
      qr_data: data.student_name ? {
        course_id: data.course_id || '',
        class_id: data.class_id || '',
        schedule_id: data.schedule_id || '',
        student_id: data.student_id || '',
        student_name: data.student_name || '',
        gender: data.gender || '',
      } : null,
      essay_clean_text: data.essay_clean_text || '',
      grammar_errors: data.grammar_errors || [],
      scores: data.scores || null,
      total_score: data.total_score || 0,
      error: data.error || null,
      thread_id: data.thread_id || '',
    }
  } catch {
    result.value = null
  } finally {
    loading.value = false
  }
}

function goBack() {
  router.go(-1)
}

onMounted(fetchResult)
</script>

<template>
  <div class="batch-result-page">
    <div class="page-header">
      <el-button text @click="goBack">← 返回作业列表</el-button>
    </div>

    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="8" animated />
    </div>

    <div v-else-if="result">
      <ResultPanel :result="result" image-base64="" :record-id="recordId" @back="goBack" :back-upload="false"/>
    </div>

    <div v-else class="error-state">
      <el-empty description="未找到批改记录" />
    </div>
  </div>
</template>

<style scoped>
.batch-result-page {
  max-width: 900px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 16px;
}

.loading-state,
.error-state {
  background: #fff;
  border-radius: 8px;
  padding: 24px;
}
</style>
