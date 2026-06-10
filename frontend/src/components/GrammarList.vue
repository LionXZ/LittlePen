<script setup lang="ts">
import type { GrammarErrorItem } from '@/types/grading'
import { errorTypeColorMap } from '@/types/grading'

defineProps<{
  errors: GrammarErrorItem[]
}>()
</script>

<template>
  <el-card>
    <template #header>
      <span class="card-title">
        语法错误批改
        <el-tag v-if="errors.length > 0" type="warning" size="small" style="margin-left: 8px">
          {{ errors.length }} 处
        </el-tag>
        <el-tag v-else type="success" size="small" style="margin-left: 8px">
          无错误
        </el-tag>
      </span>
    </template>

    <div v-if="errors.length > 0">
      <el-table :data="errors" stripe style="width: 100%">
        <el-table-column prop="original" label="原文" min-width="180">
          <template #default="{ row }">
            <span class="error-text">{{ row.original }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="corrected" label="修正建议" min-width="180">
          <template #default="{ row }">
            <span class="corrected-text">{{ row.corrected }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="error_type" label="类型" width="80" align="center">
          <template #default="{ row }">
            <el-tag
              :type="errorTypeColorMap[row.error_type] || ''"
              size="small"
            >
              {{ row.error_type }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="explanation" label="解释" min-width="150">
          <template #default="{ row }">
            <span class="explanation-text">{{ row.explanation }}</span>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-result
      v-else
      icon="success"
      title="没有发现语法错误"
      sub-title="作文语法表现很好，继续保持！"
    />
  </el-card>
</template>

<style scoped>
.card-title {
  font-size: 16px;
  font-weight: 600;
  display: flex;
  align-items: center;
}

.error-text {
  color: #e6422e;
  text-decoration: line-through;
  text-decoration-color: #e6422e55;
}

.corrected-text {
  color: #67c23a;
  font-weight: 500;
}

.explanation-text {
  color: #666;
  font-size: 13px;
}
</style>
