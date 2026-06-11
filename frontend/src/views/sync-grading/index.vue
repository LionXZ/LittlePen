<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { gradeEssay } from '@/api/essay'
import UploadPanel from '@/components/UploadPanel.vue'
import ResultPanel from '@/components/ResultPanel.vue'
import type { GradeResult } from '@/types/grading'

const imageBase64 = ref('')
const loading = ref(false)
const showResult = ref(false)
const resultData = ref<GradeResult | null>(null)

function handleFileReady(base64: string) {
  imageBase64.value = base64
  showResult.value = false
  resultData.value = null
}

async function handleStartGrading() {
  if (!imageBase64.value) return
  loading.value = true
  try {
    const data = await gradeEssay(imageBase64.value)
    if (data.error) {
      ElMessage.warning(`批改完成，但出现错误: ${data.error}`)
    }
    resultData.value = data
    showResult.value = true
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.message || '批改请求失败'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

function handleBack() {
  showResult.value = false
  resultData.value = null
}
</script>

<template>
  <div class="sync-grading-view">
    <!-- Upload -->
    <UploadPanel
      v-if="!showResult"
      @file-ready="handleFileReady"
      @start-grading="handleStartGrading"
      :disabled="loading"
    />

    <!-- Loading -->
    <div v-if="loading" class="loading-card">
      <el-card v-loading="loading" element-loading-text="正在批改中，请稍候...">
        <div style="height: 200px" />
      </el-card>
    </div>

    <!-- Result -->
    <ResultPanel
      v-if="showResult && resultData"
      :result="resultData"
      :image-base64="imageBase64"
      @back="handleBack"
    />
  </div>
</template>

<style scoped>
.sync-grading-view {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.loading-card {
  max-width: 600px;
  margin: 0 auto;
  width: 100%;
}
</style>
