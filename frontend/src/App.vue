<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Document, Clock, FolderOpened, List } from '@element-plus/icons-vue'

const route = useRoute()
const activeMenu = computed(() => route.path)
</script>

<template>
  <div class="app-layout">
    <!-- 左侧菜单栏 -->
    <aside class="app-sidebar">
      <div class="sidebar-header">
        <h2>LittlePen</h2>
        <p>儿童英文作文 AI 批改</p>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        class="sidebar-menu"
      >
        <el-menu-item index="/stream">
          <el-icon><Document /></el-icon>
          <span>流式批改</span>
        </el-menu-item>
        <el-menu-item index="/sync">
          <el-icon><Clock /></el-icon>
          <span>同步批改</span>
        </el-menu-item>
        <el-menu-item index="/batch">
          <el-icon><FolderOpened /></el-icon>
          <span>批量批改</span>
        </el-menu-item>
        <el-menu-item index="/records">
          <el-icon><List /></el-icon>
          <span>作业列表</span>
        </el-menu-item>
      </el-menu>
    </aside>

    <!-- 主内容区 -->
    <main class="app-main">
      <router-view />
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

.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.app-sidebar {
  width: 220px;
  background: #304156;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow-y: auto;
}

.sidebar-header {
  padding: 24px 20px 16px;
  color: #fff;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.sidebar-header h2 {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 1px;
}

.sidebar-header p {
  font-size: 11px;
  margin-top: 4px;
  opacity: 0.6;
}

.sidebar-menu {
  border-right: none;
  background: transparent;
  flex: 1;
}

.sidebar-menu .el-menu-item {
  color: rgba(255, 255, 255, 0.7);
}

.sidebar-menu .el-menu-item:hover {
  background: rgba(255, 255, 255, 0.08) !important;
  color: #fff !important;
}

.sidebar-menu .el-menu-item.is-active {
  background: #409eff !important;
  color: #fff !important;
}

.app-main {
  flex: 1;
  padding: 30px 32px;
  overflow-y: auto;
  height: 100vh;
}
</style>
