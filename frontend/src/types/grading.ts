/** 二维码解析数据 */
export interface QRData {
  course_id: string
  class_id: string
  schedule_id: string
  student_id: string
  student_name: string
  gender: string
}

/** 语法错误项 */
export interface GrammarErrorItem {
  original: string
  corrected: string
  error_type: string
  explanation: string
}

/** 维度评分 */
export interface DimensionScore {
  score: number
  comment: string
}

/** 四维评分 */
export interface ScoresData {
  neatness: DimensionScore
  content: DimensionScore
  language: DimensionScore
  structure: DimensionScore
}

/** 批改完整结果 */
export interface GradeResult {
  qr_data: QRData | null
  essay_clean_text: string
  grammar_errors: GrammarErrorItem[]
  scores: ScoresData | null
  total_score: number
  error: string | null
  thread_id: string
}

/** SSE 进度事件 */
export interface SSEProgressEvent {
  step: string
  data?: GradeResult
}

/** 错误类型标签颜色映射 */
export const errorTypeColorMap: Record<string, string> = {
  '语法': 'danger',
  '拼写': 'warning',
  '用词': 'info',
  '标点': '',
}

/** 评分维度中文名 */
export const dimensionLabelMap: Record<string, string> = {
  neatness: '卷面整洁',
  content: '内容要点',
  language: '语言质量',
  structure: '篇章结构',
}
