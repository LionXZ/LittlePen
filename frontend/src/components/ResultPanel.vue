<script setup lang="ts">
import type { GradeResult } from '@/types/grading'
import QRInfoCard from './QRInfoCard.vue'
import EssayTextCard from './EssayTextCard.vue'
import GrammarList from './GrammarList.vue'
import ScoreBoard from './ScoreBoard.vue'

defineProps<{
  result: GradeResult | null
  imageBase64: string
}>()

defineEmits<{
  (e: 'back'): void
}>()
</script>

<template>
  <div class="result-panel">
    <div class="result-header">
      <h2>批改结果</h2>
      <el-button type="default" @click="$emit('back')">返回上传</el-button>
    </div>

    <div v-if="result" class="result-cards">
      <!-- 二维码信息 -->
      <QRInfoCard :qr-data="result.qr_data" />

      <!-- 作文原文 -->
      <EssayTextCard :text="result.essay_clean_text" />

      <!-- 语法错误 -->
      <GrammarList :errors="result.grammar_errors" />

      <!-- 评分看板 -->
      <ScoreBoard
        :scores="result.scores"
        :total-score="result.total_score"
      />
    </div>

    <el-empty v-else description="暂无批改结果" />
  </div>
</template>

<style scoped>
.result-panel {
  max-width: 800px;
  margin: 0 auto;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.result-header h2 {
  font-size: 22px;
  color: #333;
}

.result-cards {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
</style>
