<script setup lang="ts">
import type { QRData } from '@/types/grading'
import { subjectLabelMap } from '@/types/grading'

defineProps<{
  qrData: QRData | null
}>()
</script>

<template>
  <el-card>
    <template #header>
      <span class="card-title">二维码信息</span>
    </template>

    <div v-if="qrData">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="课程 ID">
          {{ qrData.course_id }}
        </el-descriptions-item>
        <el-descriptions-item label="班级 ID">
          {{ qrData.class_id }}
        </el-descriptions-item>
        <el-descriptions-item label="排课 ID">
          {{ qrData.schedule_id }}
        </el-descriptions-item>
        <el-descriptions-item label="学号">
          {{ qrData.student_id }}
        </el-descriptions-item>
        <el-descriptions-item label="学生姓名">
          <el-tag type="primary">{{ qrData.student_name }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="性别">
          {{ qrData.gender }}
        </el-descriptions-item>
        <el-descriptions-item label="科目">
          {{ subjectLabelMap[qrData.subject || 'en'] || qrData.subject || '英语' }}
        </el-descriptions-item>
      </el-descriptions>
    </div>

    <el-empty v-else description="未识别到二维码信息" :image-size="60" />
  </el-card>
</template>

<style scoped>
.card-title {
  font-size: 16px;
  font-weight: 600;
}
</style>
