<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { GradeResult } from '@/types/grading'

const emit = defineEmits<{
  (e: 'grading-complete', result: GradeResult, imageBase64: string): void
}>()

const grading = ref(false)
const progress = ref(0)
const currentStepLabel = ref('')

const imageBase64 = ref('')
const previewUrl = ref('')
const error = ref<string | null>(null)
const uploadRef = ref()

const stepProgressMap: Record<string, number> = {
  qr_parse_done: 15,
  ocr_done: 35,
  template_remove_done: 50,
  grammar_check_done: 75,
  scoring_done: 90,
  done: 100,
}

const stepLabelMap: Record<string, string> = {
  qr_parse_done: '二维码信息识别完成',
  ocr_done: '手写内容识别完成 (GLM-5V-Turbo)',
  template_remove_done: '作文内容提取完成',
  grammar_check_done: '语法批改完成 (deepseek-v4-pro)',
  scoring_done: '评分完成 (deepseek-v4-pro)',
  done: '批改完成',
}

function handleFileChange(uploadFile: any) {
  const file = uploadFile.raw as File
  if (!file) return false
  const reader = new FileReader()
  reader.onload = (e) => {
    const result = e.target?.result as string
    previewUrl.value = result
    imageBase64.value = result.split(',')[1]
  }
  reader.readAsDataURL(file)
  return false
}

function reset() {
  grading.value = false
  progress.value = 0
  currentStepLabel.value = ''
  error.value = null
}

async function doGrading() {
  if (!imageBase64.value) {
    ElMessage.warning('请先上传答题纸图片')
    return
  }

  reset()
  grading.value = true

  try {
    const response = await fetch('/api/v1/essay/grade/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        image_base64: imageBase64.value,
        thread_id: 'default',
      }),
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const reader = response.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const payload = line.slice(6)
        if (payload === '[DONE]') continue

        try {
          const event = JSON.parse(payload)
          const step = event.step

          if (step && stepProgressMap[step] !== undefined) {
            progress.value = stepProgressMap[step]
          }
          if (step && stepLabelMap[step]) {
            currentStepLabel.value = stepLabelMap[step]
          }

          if (step === 'done' && event.data) {
            grading.value = false
            emit('grading-complete', event.data, imageBase64.value)
            return
          }

          if (step === 'error') {
            error.value = event.data?.error || '批改失败'
            grading.value = false
            ElMessage.error(error.value!)
            return
          }
        } catch {
          // ignore parse errors
        }
      }
    }
  } catch (e: any) {
    error.value = e.message || '网络错误'
    grading.value = false
    ElMessage.error(error.value!)
  }
}

function handleRemove() {
  imageBase64.value = ''
  previewUrl.value = ''
  reset()
}
</script>

<template>
  <div class="upload-panel">
    <el-card>
      <template #header>
        <span class="card-title">上传答题纸</span>
      </template>

      <el-upload
        ref="uploadRef"
        drag
        :auto-upload="false"
        :on-change="handleFileChange"
        :limit="1"
        accept="image/png,image/jpeg,image/jpg"
        :disabled="grading"
      >
        <div v-if="!previewUrl" class="upload-placeholder">
          <el-icon :size="48" color="#c0c4cc">
            <svg viewBox="0 0 1024 1024" width="1em" height="1em" fill="currentColor">
              <path d="M544 864V672h128L512 480 352 672h128v192H320c-26.5 0-48-21.5-48-48V400c0-8.8 7.2-16 16-16h448c8.8 0 16 7.2 16 16v416c0 26.5-21.5 48-48 48H544z"/>
              <path d="M304 256h416c8.8 0 16-7.2 16-16v-32c0-26.5-21.5-48-48-48H336c-26.5 0-48 21.5-48 48v32c0 8.8 7.2 16 16 16z"/>
            </svg>
          </el-icon>
          <p>将答题纸图片拖拽到此处，或点击上传</p>
          <p class="upload-hint">支持 PNG / JPG / JPEG 格式</p>
        </div>

        <img v-else :src="previewUrl" class="preview-image" />
      </el-upload>

      <div class="action-bar">
        <el-button
          v-if="previewUrl"
          type="default"
          @click="handleRemove"
          :disabled="grading"
        >
          重新选择
        </el-button>

        <el-button
          type="primary"
          :loading="grading"
          :disabled="!previewUrl"
          @click="doGrading"
        >
          {{ grading ? '批改中...' : '开始批改' }}
        </el-button>
      </div>

      <div v-if="grading || progress === 100" class="progress-area">
        <el-progress
          :percentage="progress"
          :status="progress === 100 ? 'success' : ''"
          :stroke-width="16"
        />
        <p class="progress-label">{{ currentStepLabel }}</p>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.upload-panel {
  max-width: 600px;
  margin: 0 auto;
}

.card-title {
  font-size: 18px;
  font-weight: 600;
}

.upload-placeholder {
  padding: 40px 20px;
  text-align: center;
  color: #888;
}

.upload-placeholder p {
  margin-top: 12px;
}

.upload-hint {
  font-size: 12px;
  color: #bbb;
}

.preview-image {
  width: 100%;
  max-height: 400px;
  object-fit: contain;
  border-radius: 4px;
}

.action-bar {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 20px;
}

.progress-area {
  margin-top: 24px;
}

.progress-label {
  text-align: center;
  margin-top: 10px;
  color: #666;
  font-size: 14px;
}
</style>
