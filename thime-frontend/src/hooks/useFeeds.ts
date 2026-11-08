import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { feedsApi } from '@/api/feeds'

export function useFeedList(questionId: string) {
  return useQuery({
    queryKey: ['feeds', questionId],
    queryFn: () => feedsApi.list(questionId),
    enabled: !!questionId,
  })
}

export function useSubmitAnswer(questionId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: { answerText: string; isPublic?: boolean; isAnonymous?: boolean }) =>
      feedsApi.submitAnswer(questionId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['feeds', questionId] }),
  })
}

export function useComments(questionId: string, answererUserId: string) {
  return useQuery({
    queryKey: ['comments', questionId, answererUserId],
    queryFn: () => feedsApi.getComments(questionId, answererUserId),
    enabled: !!questionId && !!answererUserId,
  })
}

export function usePostComment(questionId: string, answererUserId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (commentText: string) =>
      feedsApi.postComment(questionId, answererUserId, { commentText }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['comments', questionId, answererUserId] }),
  })
}

export function usePostReply(questionId: string, answererUserId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ commentId, replyText }: { commentId: string; replyText: string }) =>
      feedsApi.postReply(questionId, answererUserId, commentId, { replyText }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['comments', questionId, answererUserId] }),
  })
}
