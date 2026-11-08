/**
 * 기록 상세 — F3 이어 생각 추가
 */
import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useRecord, useAddFollowup } from '@/hooks/useRecords'
import { Button } from '@/components/ui/Button'
import { Textarea } from '@/components/ui/Textarea'
import { Tag } from '@/components/ui/Tag'
import dayjs from 'dayjs'

export function RecordDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [followupText, setFollowupText] = useState('')
  const [showFollowupInput, setShowFollowupInput] = useState(false)

  const { data, isLoading } = useRecord(id!)
  const addFollowup = useAddFollowup(id!)

  if (isLoading) return (
    <div className="flex flex-col gap-4 animate-pulse">
      <div className="h-6 bg-night-700 rounded w-1/2" />
      <div className="h-32 bg-night-700 rounded-2xl" />
    </div>
  )

  const record = data?.record
  if (!record) return <p className="text-night-400">기록을 찾을 수 없습니다.</p>

  async function handleAddFollowup() {
    if (!followupText.trim()) return
    await addFollowup.mutateAsync(followupText.trim())
    setFollowupText('')
    setShowFollowupInput(false)
  }

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      {/* 뒤로가기 */}
      <button
        onClick={() => navigate(-1)}
        className="text-night-400 hover:text-night-200 text-sm flex items-center gap-1 -ml-1 w-fit"
        aria-label="뒤로 가기"
      >
        ← 기록 목록
      </button>

      {/* 원본 기록 */}
      <section className="bg-night-700/40 border border-night-600/50 rounded-2xl p-5 flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <p className="text-brand-300 text-xs font-semibold uppercase tracking-wide">원본 기록</p>
          <time className="text-night-500 text-xs" dateTime={record.createdAt}>
            {dayjs(record.createdAt).format('YYYY년 M월 D일 HH:mm')}
          </time>
        </div>
        <p className="text-night-100 leading-relaxed text-sm whitespace-pre-wrap">
          {record.rawText || '음성 처리 중...'}
        </p>
      </section>

      {/* AI 요약 (F2) */}
      {record.isProcessed && (
        <section className="bg-brand-500/10 border border-brand-500/20 rounded-2xl p-5 flex flex-col gap-3 animate-slide-up">
          <p className="text-brand-300 text-xs font-semibold uppercase tracking-wide">✨ 핵심 생각</p>
          <p className="text-night-50 font-medium leading-snug">{record.summaryLine}</p>
          <div className="flex flex-wrap gap-2">
            {record.tags.map((tag) => <Tag key={tag} label={tag} />)}
          </div>
        </section>
      )}

      {/* 이어 생각 목록 (F3) */}
      {record.followups?.length > 0 && (
        <section aria-labelledby="followups-heading">
          <h2 id="followups-heading" className="text-sm font-semibold text-night-300 mb-3">
            💭 이어 생각
          </h2>
          <ol className="flex flex-col gap-3">
            {record.followups.map((f, i) => (
              <li key={i} className="bg-night-700/30 border border-night-600/30 rounded-xl p-4">
                <p className="text-night-100 text-sm leading-relaxed">{f.text}</p>
                <time className="text-night-500 text-xs mt-2 block" dateTime={f.addedAt}>
                  {dayjs(f.addedAt).format('M월 D일 HH:mm')}
                </time>
              </li>
            ))}
          </ol>
        </section>
      )}

      {/* 이어 생각 추가 */}
      {showFollowupInput ? (
        <div className="flex flex-col gap-3 animate-slide-up">
          <Textarea
            label="지금은 어떻게 생각하나요?"
            placeholder="그때 생각과 지금 생각이 달라졌나요?"
            value={followupText}
            onChange={(e) => setFollowupText(e.target.value)}
            rows={4}
            autoFocus
          />
          <div className="flex gap-2">
            <Button
              variant="ghost"
              onClick={() => { setShowFollowupInput(false); setFollowupText('') }}
              className="flex-1"
            >
              취소
            </Button>
            <Button
              onClick={handleAddFollowup}
              disabled={!followupText.trim()}
              isLoading={addFollowup.isPending}
              className="flex-1"
            >
              추가하기
            </Button>
          </div>
        </div>
      ) : (
        <Button
          variant="ghost"
          onClick={() => setShowFollowupInput(true)}
          className="w-full"
        >
          + 이어 생각 남기기
        </Button>
      )}
    </div>
  )
}
