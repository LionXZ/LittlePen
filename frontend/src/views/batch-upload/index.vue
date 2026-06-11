<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { UploadFilled } from '@element-plus/icons-vue'
import { uploadBatch, uploadBatchZip } from '@/api/essay'
import { ElMessage } from 'element-plus'
import type { UploadFile, UploadFiles } from 'element-plus'

const router = useRouter()

const uploadMode = ref<'files' | 'zip'>('files')
const uploadFiles = ref<UploadFile[]>([])
const zipUploadFile = ref<UploadFile | null>(null)
const uploading = ref(false)

const canUpload = computed(() => {
  if (uploadMode.value === 'files') return uploadFiles.value.length > 0
  return zipUploadFile.value !== null
})

function handleFilesChange(_file: UploadFile, fileListNew: UploadFiles) {
  uploadFiles.value = fileListNew
}

function handleZipChange(file: UploadFile) {
  zipUploadFile.value = file
}

async function handleUpload() {
  uploading.value = true
  try {
    let res
    if (uploadMode.value === 'files') {
      const rawFiles = uploadFiles.value.map((f) => f.raw!).filter(Boolean)
      res = await uploadBatch(rawFiles)
    } else {
      res = await uploadBatchZip(zipUploadFile.value!.raw!)
    }
    ElMessage.success(`已创建批量批改任务，共 ${res.total} 份作业，请在作业列表中查看进度`)
    router.push('/records')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '上传失败')
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <div class="batch-upload-page">
    <h2>批量批改</h2>
    <p class="subtitle">支持一次上传多张答题纸图片或上传 ZIP 压缩包</p>

    <!-- 模式切换 -->
    <div class="mode-switch">
      <el-radio-group v-model="uploadMode">
        <el-radio-button value="files">多文件上传</el-radio-button>
        <el-radio-button value="zip">ZIP 压缩包</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 多文件上传 -->
    <div v-if="uploadMode === 'files'" class="upload-area">
      <el-upload
        drag
        multiple
        :auto-upload="false"
        :on-change="handleFilesChange"
        :file-list="uploadFiles"
        accept="image/png,image/jpeg,image/jpg"
        :limit="50"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          将答题纸图片拖到此处，或 <em>点击选择</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">支持 PNG / JPG / JPEG 格式，单文件不超过 10MB</div>
        </template>
      </el-upload>
    </div>

    <!-- ZIP 上传 -->
    <div v-if="uploadMode === 'zip'" class="upload-area">
      <el-upload
        drag
        :auto-upload="false"
        :on-change="handleZipChange"
        :file-list="zipUploadFile ? [zipUploadFile as any] : []"
        accept=".zip"
        :limit="1"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          将 ZIP 压缩包拖到此处，或 <em>点击选择</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">压缩包内应包含答题纸图片（PNG/JPG/JPEG），单文件不超过 10MB</div>
        </template>
      </el-upload>
    </div>

    <div class="action-bar">
      <el-button
        type="primary"
        size="large"
        :disabled="!canUpload"
        :loading="uploading"
        @click="handleUpload"
      >
        {{ uploading ? '上传中...' : '开始批量批改' }}
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.batch-upload-page {
  max-width: 640px;
  margin: 0 auto;
}

h2 {
  font-size: 24px;
  margin-bottom: 8px;
}

.subtitle {
  color: #909399;
  margin-bottom: 24px;
}

.mode-switch {
  margin-bottom: 24px;
}

.upload-area {
  margin-bottom: 24px;
}

.action-bar {
  text-align: center;
  margin-top: 16px;
}
</style>
