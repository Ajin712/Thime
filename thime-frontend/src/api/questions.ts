import { api } from '@/lib/apiClient'
import type { Question } from '@/types'

export const questionsApi = {
  // F4: 오늘의 질문
  getToday: () =>
    api.get<{ question: Question }>('/questions/today'),
}
