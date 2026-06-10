<script setup lang="ts">
defineProps<{
  text: string
}>()
</script>

<template>
  <el-card>
    <template #header>
      <span class="card-title">手写作文原文</span>
    </template>

    <div v-if="text" class="essay-text">
      {{ text }}
    </div>

    <el-empty v-else description="未识别到作文内容" :image-size="60" />
  </el-card>
</template>

<style scoped>
.card-title {
  font-size: 16px;
  font-weight: 600;
}

.essay-text {
  white-space: pre-wrap;
  line-height: 1.8;
  font-size: 15px;
  color: #333;
  padding: 12px;
  background: #f9fafb;
  border-radius: 6px;
  border-left: 3px solid #409eff;
}
</style>
