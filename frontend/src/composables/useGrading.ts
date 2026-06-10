import { ref, reactive } from 'vue'
import type { GradeResult, SSEProgressEvent } from '@/types/grading'

const stepProgressMap: Record<string, number> = {
  start: 0,
  qr_parse_done: 15,
  ocr_done: 35,
  template_remove_done: 50,
  grammar_check_done: 75,
  scoring_done: 90,
  done: 100,
}

const stepLabelMap: Record<string, string> = {
  start: '准备中...',
  qr_parse_done: '二维码信息识别完成',
  ocr_done: '手写内容识别完成',
  template_remove_done: '作文内容提取完成',
  grammar_check_done: '语法批改完成',
  scoring_done: '评分完成',
  done: '批改完成',
}

export function useGrading() {
  const grading = ref(false)
  const currentStep = ref('')
  const currentStepLabel = ref('')
  const progress = ref(0)
  const result = ref<GradeResult | null>(null)
  const error = ref<string | null>(null)

  function reset() {
    grading.value = false
    currentStep.value = ''
    currentStepLabel.value = ''
    progress.value = 0
    result.value = null
    error.value = null
  }

  async function startGrading(imageBase64: string) {
    reset()
    grading.value = true
    currentStep.value = 'start'
    currentStepLabel.value = stepLabelMap.start
    progress.value = 0

    try {
      const response = await fetch('/api/v1/essay/grade/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image_base64: imageBase64,
          thread_id: 'default',
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const payload = line.slice(6)

            if (payload === '[DONE]') {
              continue
            }

            try {
              const event: SSEProgressEvent = JSON.parse(payload)
              currentStep.value = event.step

              if (stepLabelMap[event.step]) {
                currentStepLabel.value = stepLabelMap[event.step]
              }

              if (stepProgressMap[event.step] !== undefined) {
                progress.value = stepProgressMap[event.step]
              }

              if (event.step === 'done' && event.data) {
                result.value = event.data
              }

              if (event.step === 'error') {
                error.value = event.data?.error || '批改失败'
                grading.value = false
                return
              }
            } catch {
              // 忽略解析失败的行
            }
          }
        }
      }
    } catch (e: any) {
      error.value = e.message || '网络错误'
    } finally {
      grading.value = false
    }
  }

  return {
    grading,
    currentStep,
    currentStepLabel,
    progress,
    result,
    error,
    reset,
    startGrading,
  }
}
