import { api } from '@/lib/apiClient'
import type { Record } from '@/types'

export interface CreateRecordPayload {
  rawText: string
}

export interface AddFollowupPayload {
  text: string
}

export interface AudioUrlPayload {
  recordId: string
  fileExt: 'webm' | 'mp4' | 'm4a'
}

export const recordsApi = {
  // F1: 텍스트 기록 저장
  create: (payload: CreateRecordPayload) =>
    api.post<{ record: Record }>('/records', payload),

  // F1: 내 기록 목록
  list: (limit = 20) =>
    api.get<{ records: Record[]; count: number }>(`/records?limit=${limit}`),

  // F1: 기록 상세
  get: (recordId: string) =>
    api.get<{ record: Record }>(`/records/${recordId}`),

  // F1: 기록 삭제
  delete: (recordId: string) =>
    api.delete<{ message: string }>(`/records/${recordId}`),

  // F1: presigned URL 발급 (음성 업로드)
  getAudioUploadUrl: (payload: AudioUrlPayload) =>
    api.post<{ uploadUrl: string; s3Key: string }>('/records/audio-url', payload),

  // F2: 요약·태그 추출 (Bedrock)
  summarize: (recordId: string) =>
    api.post<{ summaryLine: string; tags: string[] }>(`/records/${recordId}/summarize`, {}),

  // F3: 이어 생각 추가
  addFollowup: (recordId: string, payload: AddFollowupPayload) =>
    api.patch<{ message: string }>(`/records/${recordId}/followup`, payload),
}

// 음성 파일을 S3에 직접 업로드 (presigned URL 사용)
export async function uploadAudioToS3(uploadUrl: string, audioBlob: Blob): Promise<void> {
  const res = await fetch(uploadUrl, {
    method: 'PUT',
    body: audioBlob,
    headers: { 'Content-Type': audioBlob.type },
  })
  if (!res.ok) throw new Error('음성 업로드에 실패했습니다.')
}
