<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
  (e: 'file-ready', imageBase64: string): void
  (e: 'start-grading'): void
}>()

defineProps<{
  disabled?: boolean
}>()

const imageBase64 = ref('')
const previewUrl = ref('')
const uploadRef = ref()

function handleFileChange(uploadFile: any) {
  const file = uploadFile.raw as File
  if (!file) return false
  const reader = new FileReader()
  reader.onload = (e) => {
    const result = e.target?.result as string
    previewUrl.value = result
    imageBase64.value = result.split(',')[1]
    emit('file-ready', imageBase64.value)
  }
  reader.readAsDataURL(file)
  return false
}

function handleRemove() {
  imageBase64.value = ''
  previewUrl.value = ''
}

function handleStart() {
  if (!imageBase64.value) return
  emit('start-grading')
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
        :disabled="disabled"
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
          :disabled="disabled"
        >
          重新选择
        </el-button>

        <el-button
          type="primary"
          :loading="disabled"
          :disabled="!previewUrl"
          @click="handleStart"
        >
          {{ disabled ? '批改中...' : '开始批改' }}
        </el-button>
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
</style>
