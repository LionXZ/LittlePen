<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { listRecords } from '@/api/essay'
import { batchStatusMap } from '@/types/grading'
import type { RecordSummary } from '@/api/essay'

const router = useRouter()
const records = ref<RecordSummary[]>([])
const loading = ref(true)
let timer: ReturnType<typeof setInterval> | null = null

async function fetchRecords() {
  try {
    const data = await listRecords(100, 0)
    records.value = data.items
  } finally {
    loading.value = false
  }
}

function goResult(record: RecordSummary) {
  if (record.batch_id) {
    router.push(`/batch/${record.batch_id}/result/${record.id}`)
  } else {
    router.push(`/batch/_single/result/${record.id}`)
  }
}

function formatTime(iso: string) {
  if (!iso) return '-'
  return iso.replace('T', ' ').slice(0, 19)
}

onMounted(() => {
  fetchRecords()
  timer = setInterval(fetchRecords, 10_000)
})

onUnmounted(() => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
})
</script>

<template>
  <div class="records-list-page">
    <div class="page-header">
      <h2>作业列表</h2>
      <p class="subtitle">全部批改记录</p>
    </div>

    <div class="content-card">
      <el-table v-if="!loading" :data="records" stripe>
        <el-table-column prop="filename" label="文件名" min-width="160">
          <template #default="{ row }">{{ row.filename || '-' }}</template>
        </el-table-column>
        <el-table-column prop="student_name" label="学生姓名" width="100">
          <template #default="{ row }">{{ row.student_name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="student_id" label="学号" width="120" />
        <el-table-column prop="class_id" label="班级" width="80" />
        <el-table-column label="批改状态" width="100">
          <template #default="{ row }">
            <el-tag
              :type="batchStatusMap[row.status]?.type || 'info'"
              size="small"
            >
              {{ batchStatusMap[row.status]?.label || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="总分" width="70">
          <template #default="{ row }">
            <span v-if="row.status === 2">{{ row.total_score }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="提交时间" width="160">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 2"
              type="primary"
              size="small"
              text
              @click="goResult(row)"
            >
              查看详情
            </el-button>
            <span
              v-else-if="row.status === 3"
              class="error-text"
            >
              {{ row.error_msg?.slice(0, 20) || '失败' }}
            </span>
          </template>
        </el-table-column>
      </el-table>

      <el-skeleton v-else :rows="8" animated />
    </div>
  </div>
</template>

<style scoped>
.records-list-page {
  max-width: 1000px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h2 {
  font-size: 24px;
}

.subtitle {
  color: #909399;
  margin-top: 4px;
}

.content-card {
  background: #fff;
  border-radius: 8px;
  padding: 24px;
}

.text-muted {
  color: #c0c4cc;
}

.error-text {
  color: #f56c6c;
  font-size: 12px;
}
</style>
