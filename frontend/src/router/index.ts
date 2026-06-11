import { createRouter, createWebHashHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/stream',
  },
  {
    path: '/stream',
    name: 'StreamGrading',
    component: () => import('@/views/stream-grading/index.vue'),
  },
  {
    path: '/sync',
    name: 'SyncGrading',
    component: () => import('@/views/sync-grading/index.vue'),
  },
  {
    path: '/batch',
    name: 'BatchUpload',
    component: () => import('@/views/batch-upload/index.vue'),
  },
  {
    path: '/batch/:batchId/result/:recordId',
    name: 'BatchResult',
    component: () => import('@/views/batch-result/index.vue'),
  },
  {
    path: '/records',
    name: 'RecordsList',
    component: () => import('@/views/records-list/index.vue'),
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
