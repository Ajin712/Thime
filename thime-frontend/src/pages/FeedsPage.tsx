/**
 * 다른 생각 보기 (F5) + 버블 댓글
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { questionsApi } from '@/api/questions'
import { useFeedList, useSubmitAnswer, usePostComment } from '@/hooks/useFeeds'
import { Button } from '@/components/ui/Button'
import { Textarea } from '@/components/ui/Textarea'
import type { Feed } from '@/types'
import dayjs from 'dayjs'

export function FeedsPage() {
  const { data: questionData } = useQuery({
    queryKey: ['question-today'],
    queryFn: questionsApi.getToday,
  })

  const questionId = questionData?.question?.questionId ?? ''
  const { data: feedData, isLoading } = useFeedList(questionId)

  const [answerText, setAnswerText] = useState('')
  const [isAnonymous, setIsAnonymous] = useState(true)
  const submitAnswer = useSubmitAnswer(questionId)

  async function handleSubmit() {
    if (!answerText.trim()) return
    await submitAnswer.mutateAsync({ answerText: answerText.trim(), isPublic: true, isAnonymous })
    setAnswerText('')
  }

  if (!questionData) return null
  const question = questionData.question

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      <h2 className="text-xl font-bold">다른 생각 보기</h2>

      {/* 질문 */}
      <div className="bg-brand-500/10 border border-brand-500/25 rounded-2xl p-5">
        <p className="text-brand-300 text-xs font-semibold mb-2 uppercase tracking-wide">🌙 오늘의 질문</p>
        <p className="text-night-50 text-lg font-medium leading-snug">{question.content}</p>
      </div>

      {/* 잠금 상태 — 내 답 먼저 */}
      {feedData?.locked !== false && (
        <div className="flex flex-col gap-4 bg-night-700/40 border border-night-600/50 rounded-2xl p-5">
          <p className="text-night-300 text-sm leading-relaxed">
            🔒 먼저 내 생각을 남겨야 다른 사람들의 생각을 볼 수 있어요.
          </p>
          <Textarea
            placeholder="내 생각을 먼저 써보세요..."
            value={answerText}
            onChange={(e) => setAnswerText(e.target.value)}
            rows={4}
          />
          <label className="flex items-center gap-2 text-sm text-night-300 cursor-pointer w-fit">
            <input
              type="checkbox"
              checked={isAnonymous}
              onChange={(e) => setIsAnonymous(e.target.checked)}
              className="accent-brand-500"
            />
            익명으로 공유
          </label>
          <Button
            onClick={handleSubmit}
            disabled={!answerText.trim()}
            isLoading={submitAnswer.isPending}
            className="w-full"
          >
            내 생각 남기기 →
          </Button>
        </div>
      )}

      {/* 내 답변 표시 */}
      {feedData?.myAnswer && (
        <div className="bg-brand-500/8 border border-brand-500/20 rounded-2xl p-4">
          <p className="text-brand-300 text-xs font-semibold mb-2">내 생각</p>
          <p className="text-night-100 text-sm leading-relaxed">{feedData.myAnswer.answerText}</p>
        </div>
      )}

      {/* 다른 사람들의 답변 목록 */}
      {feedData?.locked === false && (
        <section aria-labelledby="others-heading">
          <h3 id="others-heading" className="text-sm font-semibold text-night-300 mb-3">
            💬 다른 사람들의 생각 ({feedData.count}개)
          </h3>
          {isLoading && <LoadingCards />}
          {feedData.feeds.length === 0 && (
            <p className="text-night-500 text-sm text-center py-8">아직 아무도 공유하지 않았어요.</p>
          )}
          <ul className="flex flex-col gap-3">
            {feedData.feeds.map((feed) => (
              <FeedCard
                key={`${feed.questionId}-${feed.answererUserId}`}
                feed={feed}
                questionId={questionId}
              />
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}

// ─── 개별 피드 카드 ───────────────────────────────────────────
function FeedCard({ feed, questionId }: { feed: Feed; questionId: string }) {
  const [showComment, setShowComment] = useState(false)
  const [commentText, setCommentText] = useState('')
  const postComment = usePostComment(questionId, feed.answererUserId)

  async function handlePostComment() {
    if (!commentText.trim()) return
    await postComment.mutateAsync(commentText.trim())
    setCommentText('')
    setShowComment(false)
  }

  return (
    <li className="bg-night-700/40 border border-night-600/50 rounded-2xl p-4 flex flex-col gap-3">
      <p className="text-night-100 text-sm leading-relaxed">{feed.answerText}</p>
      <div className="flex items-center justify-between">
        <time className="text-night-500 text-xs" dateTime={feed.createdAt}>
          {dayjs(feed.createdAt).format('M/D HH:mm')}
        </time>
        <button
          onClick={() => setShowComment((v) => !v)}
          className="text-night-400 hover:text-brand-300 text-xs transition-colors"
          aria-expanded={showComment}
        >
          💬 댓글 달기
        </button>
      </div>

      {/* 댓글 입력 (버블 메커니즘) */}
      {showComment && (
        <div className="flex flex-col gap-2 pt-2 border-t border-night-600/50 animate-slide-up">
          <Textarea
            placeholder="이 생각에 대해 한 마디..."
            value={commentText}
            onChange={(e) => setCommentText(e.target.value)}
            rows={2}
            className="text-xs"
            autoFocus
          />
          <div className="flex gap-2 justify-end">
            <Button variant="ghost" size="sm" onClick={() => setShowComment(false)}>
              취소
            </Button>
            <Button
              size="sm"
              onClick={handlePostComment}
              disabled={!commentText.trim()}
              isLoading={postComment.isPending}
            >
              보내기
            </Button>
          </div>
        </div>
      )}
    </li>
  )
}

function LoadingCards() {
  return (
    <div className="flex flex-col gap-3" aria-busy>
      {[...Array(3)].map((_, i) => (
        <div key={i} className="bg-night-700/40 border border-night-600/50 rounded-2xl p-4 animate-pulse h-20" />
      ))}
    </div>
  )
}
