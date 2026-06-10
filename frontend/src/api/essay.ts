import axios from 'axios'
import type { GradeResult } from '@/types/grading'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 120000,
})

/** 同步批改 - base64 图片 */
export async function gradeEssay(
  imageBase64: string,
  threadId = 'default',
): Promise<GradeResult> {
  const { data } = await api.post<GradeResult>('/essay/grade', {
    image_base64: imageBase64,
    thread_id: threadId,
  })
  return data
}

/** 上传图片文件批改 */
export async function gradeEssayUpload(
  file: File,
  threadId = 'default',
): Promise<GradeResult> {
  const form = new FormData()
  form.append('file', file)
  form.append('thread_id', threadId)
  const { data } = await api.post<GradeResult>('/essay/grade/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

/** 查询历史批改记录 */
export async function getGradingRecord(recordId: string): Promise<GradeResult> {
  const { data } = await api.get<GradeResult>(`/essay/${recordId}`)
  return data
}

/** 健康检查 */
export async function healthCheck(): Promise<{ status: string; version: string }> {
  const { data } = await api.get('/health')
  return data
}

/** 获取 SSE 流式批改 URL */
export function getStreamUrl(imageBase64: string, threadId = 'default'): string {
  return `/api/v1/essay/grade/stream`
}

/** 发起 SSE 流式批改请求 */
export function gradeEssayStream(
  imageBase64: string,
  threadId = 'default',
): Promise<Response> {
  return fetch('/api/v1/essay/grade/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      image_base64: imageBase64,
      thread_id: threadId,
    }),
  })
}
