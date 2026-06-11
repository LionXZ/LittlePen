<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useGrading } from '@/composables/useGrading'
import UploadPanel from '@/components/UploadPanel.vue'
import ResultPanel from '@/components/ResultPanel.vue'

const imageBase64 = ref('')
const showResult = ref(false)

const {
  grading,
  currentStepLabel,
  progress,
  result,
  error,
  startGrading,
  reset: resetGrading,
} = useGrading()

function handleFileReady(base64: string) {
  imageBase64.value = base64
  resetGrading()
  showResult.value = false
}

async function handleStartGrading() {
  if (!imageBase64.value) return
  await startGrading(imageBase64.value)
  if (result.value) {
    showResult.value = true
  }
}

watch(error, (err) => {
  if (err) {
    ElMessage.error(err)
  }
})

function handleBack() {
  showResult.value = false
  resetGrading()
}
</script>

<template>
  <div class="stream-grading-view">
    <!-- Upload -->
    <UploadPanel
      v-if="!showResult"
      @file-ready="handleFileReady"
      @start-grading="handleStartGrading"
      :disabled="grading"
    />

    <!-- Progress -->
    <div v-if="grading && !showResult" class="progress-card">
      <el-card>
        <el-progress
          :percentage="progress"
          :status="progress === 100 ? 'success' : ''"
          :stroke-width="16"
        />
        <p class="progress-label">{{ currentStepLabel }}</p>
      </el-card>
    </div>

    <!-- Result -->
    <ResultPanel
      v-if="showResult && result"
      :result="result"
      :image-base64="imageBase64"
      @back="handleBack"
    />
  </div>
</template>

<style scoped>
.stream-grading-view {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.progress-card {
  max-width: 600px;
  margin: 0 auto;
  width: 100%;
}

.progress-label {
  text-align: center;
  margin-top: 12px;
  color: #666;
  font-size: 14px;
}
</style>
