<script setup lang="ts">
import { ref } from 'vue'
import UploadPanel from './components/UploadPanel.vue'
import ResultPanel from './components/ResultPanel.vue'
import type { GradeResult } from './types/grading'

const showResult = ref(false)
const resultData = ref<GradeResult | null>(null)
const uploadedImageBase64 = ref('')

function handleGradingComplete(result: GradeResult, imageBase64: string) {
  resultData.value = result
  uploadedImageBase64.value = imageBase64
  showResult.value = true
}

function handleBack() {
  showResult.value = false
  resultData.value = null
  uploadedImageBase64.value = ''
}
</script>

<template>
  <div class="app-container">
    <header class="app-header">
      <h1>儿童英文作文 AI 批改</h1>
    </header>

    <main class="app-main">
      <UploadPanel
        v-if="!showResult"
        @grading-complete="handleGradingComplete"
      />

      <ResultPanel
        v-else
        :result="resultData"
        :image-base64="uploadedImageBase64"
        @back="handleBack"
      />
    </main>
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
    'Helvetica Neue', Arial, sans-serif;
  background: #f5f7fa;
  color: #333;
}

.app-container {
  min-height: 100vh;
}

.app-header {
  background: #409eff;
  color: #fff;
  padding: 20px 40px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.app-header h1 {
  font-size: 24px;
  font-weight: 600;
}

.app-main {
  max-width: 960px;
  margin: 0 auto;
  padding: 30px 20px;
}
</style>
