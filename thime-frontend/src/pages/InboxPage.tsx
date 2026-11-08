/**
 * 편지함 — 버블 메커니즘
 * 답변자: 내 답변에 달린 댓글 목록 + 선택적 답장
 * 댓글 작성자: 답장 확인
 */
import { useState } from 'react'
import { useAuthStore } from '@/stores/authStore'
import { useComments, usePostReply } from '@/hooks/useFeeds'
import { useQuery } from '@tanstack/react-query'
import { questionsApi } from '@/api/questions'
import { Button } from '@/components/ui/Button'
import { Textarea } from '@/components/ui/Textarea'
import type { Comment } from '@/types'
import dayjs from 'dayjs'
import { clsx } from 'clsx'

export function InboxPage() {
  const { userId } = useAuthStore()
  const { data: questionData } = useQuery({
    queryKey: ['question-today'],
    queryFn: questionsApi.getToday,
  })

  const questionId = questionData?.question?.questionId ?? ''
  const answererUserId = userId ?? ''

  const { data, isLoading } = useComments(questionId, answererUserId)

  if (!userId) return <p className="text-night-400 text-sm">로그인이 필요합니다.</p>
  if (isLoading) return <LoadingSkeleton />

  const comments = data?.comments ?? []
  const unreadCount = data?.unreadCount ?? 0

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      <header className="flex items-center justify-between">
        <h2 className="text-xl font-bold">편지함</h2>
        {unreadCount > 0 && (
          <span className="bg-brand-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
            {unreadCount}
          </span>
        )}
      </header>

      {data?.role === 'answerer' && (
        <p className="text-night-400 text-xs">
          내 답변에 달린 댓글이에요. 답장하고 싶은 댓글에만 선택적으로 답장할 수 있어요.
        </p>
      )}

      {comments.length === 0 && (
        <div className="text-center py-16 text-night-400">
          <p className="text-4xl mb-3">✉️</p>
          <p className="text-sm">아직 받은 댓글이 없어요.</p>
        </div>
      )}

      <ul className="flex flex-col gap-4">
        {comments.map((comment) => (
          <CommentItem
            key={comment.commentId}
            comment={comment}
            questionId={questionId}
            answererUserId={answererUserId}
            role={data?.role ?? 'commenter'}
          />
        ))}
      </ul>
    </div>
  )
}

// ─── 댓글 아이템 ───────────────────────────────────────────────
function CommentItem({
  comment,
  questionId,
  answererUserId,
  role,
}: {
  comment: Comment
  questionId: string
  answererUserId: string
  role: 'answerer' | 'commenter'
}) {
  const [showReply, setShowReply] = useState(false)
  const [replyText, setReplyText] = useState('')
  const postReply = usePostReply(questionId, answererUserId)

  async function handleReply() {
    if (!replyText.trim()) return
    await postReply.mutateAsync({ commentId: comment.commentId, replyText: replyText.trim() })
    setReplyText('')
    setShowReply(false)
  }

  const hasReplied = role === 'answerer' ? comment.hasReplied : comment.hasReply

  return (
    <li className={clsx(
      'bg-night-700/40 border rounded-2xl p-4 flex flex-col gap-3',
      !comment.isRead && role === 'answerer' ? 'border-brand-500/40' : 'border-night-600/50',
    )}>
      {/* 안 읽은 표시 */}
      {!comment.isRead && role === 'answerer' && (
        <span className="text-brand-300 text-xs font-semibold">🆕 새 댓글</span>
      )}

      {/* 댓글 내용 */}
      <div>
        {role === 'answerer' && comment.commenterUserId && (
          <p className="text-night-500 text-xs mb-1">익명</p>
        )}
        <p className="text-night-100 text-sm leading-relaxed">{comment.commentText}</p>
        <time className="text-night-500 text-xs mt-1.5 block" dateTime={comment.createdAt}>
          {dayjs(comment.createdAt).format('M/D HH:mm')}
        </time>
      </div>

      {/* 답장 영역 */}
      {comment.replyText && (
        <div className="bg-brand-500/10 border border-brand-500/20 rounded-xl p-3 animate-slide-up">
          <p className="text-brand-300 text-xs font-semibold mb-1">
            {role === 'answerer' ? '내 답장' : '답장이 왔어요 ✨'}
          </p>
          <p className="text-night-100 text-sm leading-relaxed">{comment.replyText}</p>
          {comment.repliedAt && (
            <time className="text-night-500 text-xs mt-1 block" dateTime={comment.repliedAt}>
              {dayjs(comment.repliedAt).format('M/D HH:mm')}
            </time>
          )}
        </div>
      )}

      {/* 답장 버튼 — 답변자만, 아직 답장 안 한 경우 */}
      {role === 'answerer' && !hasReplied && !showReply && (
        <button
          onClick={() => setShowReply(true)}
          className="text-brand-400 hover:text-brand-300 text-xs self-start transition-colors"
        >
          답장하기 →
        </button>
      )}

      {role === 'answerer' && hasReplied && !showReply && (
        <button
          onClick={() => setShowReply(true)}
          className="text-night-500 hover:text-night-300 text-xs self-start transition-colors"
        >
          답장 수정
        </button>
      )}

      {/* 답장 입력 */}
      {showReply && role === 'answerer' && (
        <div className="flex flex-col gap-2 pt-2 border-t border-night-600/50 animate-slide-up">
          <Textarea
            placeholder="댓글에 답장을 보내세요. 이 분에게만 보여요."
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            rows={3}
            autoFocus
          />
          <p className="text-night-500 text-xs">🔒 이 분에게만 보이는 1:1 답장이에요.</p>
          <div className="flex gap-2 justify-end">
            <Button variant="ghost" size="sm" onClick={() => { setShowReply(false); setReplyText('') }}>
              취소
            </Button>
            <Button
              size="sm"
              onClick={handleReply}
              disabled={!replyText.trim()}
              isLoading={postReply.isPending}
            >
              보내기
            </Button>
          </div>
        </div>
      )}
    </li>
  )
}

function LoadingSkeleton() {
  return (
    <div className="flex flex-col gap-4" aria-busy>
      {[...Array(3)].map((_, i) => (
        <div key={i} className="bg-night-700/40 border border-night-600/50 rounded-2xl p-4 animate-pulse h-28" />
      ))}
    </div>
  )
}
