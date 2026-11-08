import { api } from '@/lib/apiClient'
import type { FeedListResponse, CommentsResponse } from '@/types'

export interface SubmitAnswerPayload {
  answerText: string
  isPublic?: boolean
  isAnonymous?: boolean
}

export interface PostCommentPayload {
  commentText: string
}

export interface PostReplyPayload {
  replyText: string
}

export const feedsApi = {
  // F5: 다른 생각 보기 (내 답 먼저 있어야 열림)
  list: (questionId: string) =>
    api.get<FeedListResponse>(`/feeds/${questionId}`),

  // F5: 내 답 공유
  submitAnswer: (questionId: string, payload: SubmitAnswerPayload) =>
    api.post<{ message: string }>(`/feeds/${questionId}`, payload),

  // 버블: 댓글 달기
  postComment: (questionId: string, answererUserId: string, payload: PostCommentPayload) =>
    api.post<{ message: string; commentId: string }>(
      `/feeds/${questionId}/${answererUserId}/comments`,
      payload,
    ),

  // 버블: 댓글 조회 (답변자: 전체 / 댓글 작성자: 내 댓글만)
  getComments: (questionId: string, answererUserId: string) =>
    api.get<CommentsResponse>(
      `/feeds/${questionId}/${answererUserId}/comments`,
    ),

  // 버블: 답변자가 댓글에 답장
  postReply: (questionId: string, answererUserId: string, commentId: string, payload: PostReplyPayload) =>
    api.post<{ message: string; repliedAt: string }>(
      `/feeds/${questionId}/${answererUserId}/comments/${encodeURIComponent(commentId)}/reply`,
      payload,
    ),

  // 버블: 댓글 작성자가 답장 확인
  getReply: (questionId: string, answererUserId: string, commentId: string) =>
    api.get<{ hasReply: boolean; replyText: string | null }>(
      `/feeds/${questionId}/${answererUserId}/comments/${encodeURIComponent(commentId)}/reply`,
    ),
}
