import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { recordsApi, uploadAudioToS3 } from '@/api/records'

export function useRecordList() {
  return useQuery({
    queryKey: ['records'],
    queryFn: () => recordsApi.list(),
  })
}

export function useRecord(recordId: string) {
  return useQuery({
    queryKey: ['records', recordId],
    queryFn: () => recordsApi.get(recordId),
    enabled: !!recordId,
  })
}

// F1: 텍스트로 기록 저장
export function useCreateRecord() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (rawText: string) => recordsApi.create({ rawText }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['records'] }),
  })
}

// F1: 음성 업로드 → Transcribe 자동 트리거
export function useUploadAudio() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ audioBlob, fileExt }: { audioBlob: Blob; fileExt: string }) => {
      // 1) 텍스트 기록 먼저 생성 (placeholder)
      const { record } = await recordsApi.create({ rawText: '' })
      const id = record.recordId

      // 2) presigned URL 발급
      const { uploadUrl } = await recordsApi.getAudioUploadUrl({
        recordId: id,
        fileExt: fileExt as 'webm' | 'mp4' | 'm4a',
      })

      // 3) S3 직접 업로드
      await uploadAudioToS3(uploadUrl, audioBlob)

      return id
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['records'] }),
  })
}

// F2: 요약·태그 추출
export function useSummarize() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (recordId: string) => recordsApi.summarize(recordId),
    onSuccess: (_data, recordId) => {
      qc.invalidateQueries({ queryKey: ['records', recordId] })
      qc.invalidateQueries({ queryKey: ['records'] })
    },
  })
}

// F3: 이어 생각 추가
export function useAddFollowup(recordId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (text: string) => recordsApi.addFollowup(recordId, { text }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['records', recordId] })
      qc.invalidateQueries({ queryKey: ['records'] })
    },
  })
}
