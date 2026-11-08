/**
 * 홈 — 오늘의 질문 + 음성/텍스트 기록 입력 (F4·F1·F2 데모 흐름 시작점)
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { questionsApi } from '@/api/questions'
import { useVoiceRecorder } from '@/hooks/useVoiceRecorder'
import { useCreateRecord, useUploadAudio, useSummarize } from '@/hooks/useRecords'
import { Button } from '@/components/ui/Button'
import { Textarea } from '@/components/ui/Textarea'
import { Tag } from '@/components/ui/Tag'
import dayjs from 'dayjs'

type InputMode = 'text' | 'voice'

export function HomePage() {
  const navigate = useNavigate()
  const [mode, setMode] = useState<InputMode>('voice')
  const [text, setText] = useState('')
  const [savedRecordId, setSavedRecordId] = useState<string | null>(null)
  const [summary, setSummary] = useState<{ summaryLine: string; tags: string[] } | null>(null)

  const { data: questionData } = useQuery({
    queryKey: ['question-today'],
    queryFn: questionsApi.getToday,
  })

  const recorder = useVoiceRecorder()
  const createRecord = useCreateRecord()
  const uploadAudio  = useUploadAudio()
  const summarize    = useSummarize()

  // ── 텍스트 저장 ──
  async function handleSaveText() {
    if (!text.trim()) return
    const { record } = await createRecord.mutateAsync(text.trim())
    setSavedRecordId(record.recordId)
    const result = await summarize.mutateAsync(record.recordId)
    setSummary(result)
    setText('')
  }

  // ── 음성 저장 ──
  async function handleSaveAudio() {
    if (!recorder.audioBlob) return
    const recordId = await uploadAudio.mutateAsync({
      audioBlob: recorder.audioBlob,
      fileExt: recorder.fileExt,
    })
    setSavedRecordId(recordId)
    recorder.reset()
  }

  const isSaving = createRecord.isPending || uploadAudio.isPending || summarize.isPending
  const question = questionData?.question

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      {/* 헤더 */}
      <header>
        <p className="text-night-400 text-xs">{dayjs().format('M월 D일 dddd')}</p>
        <h1 className="text-xl font-bold text-night-50 mt-0.5">안녕하세요 👋</h1>
      </header>

      {/* 오늘의 질문 카드 (F4) */}
      {question && (
        <section
          className="bg-brand-500/10 border border-brand-500/25 rounded-2xl p-5"
          aria-labelledby="today-question"
        >
          <p className="text-brand-300 text-xs font-semibold mb-2 tracking-wide uppercase">
            🌙 오늘의 질문
          </p>
          <p id="today-question" className="text-night-50 text-lg font-medium leading-snug">
            {question.content}
          </p>
        </section>
      )}

      {/* 입력 영역 */}
      <section className="bg-night-700/40 border border-night-600/50 rounded-2xl p-5 flex flex-col gap-4">
        {/* 모드 탭 */}
        <div className="flex gap-2 bg-night-800/60 p-1 rounded-xl w-fit">
          {(['voice', 'text'] as InputMode[]).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`text-sm px-4 py-1.5 rounded-lg transition-colors font-medium ${
                mode === m
                  ? 'bg-brand-500 text-white'
                  : 'text-night-400 hover:text-night-200'
              }`}
              aria-pressed={mode === m}
            >
              {m === 'voice' ? '🎙 음성' : '✏️ 텍스트'}
            </button>
          ))}
        </div>

        {/* 텍스트 모드 */}
        {mode === 'text' && (
          <div className="flex flex-col gap-3 animate-fade-in">
            <Textarea
              placeholder="지금 머릿속에 있는 생각을 그대로 써보세요..."
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={5}
              aria-label="생각 입력"
            />
            <Button
              onClick={handleSaveText}
              disabled={!text.trim()}
              isLoading={isSaving}
              className="w-full"
            >
              기록 남기기
            </Button>
          </div>
        )}

        {/* 음성 모드 */}
        {mode === 'voice' && (
          <div className="flex flex-col items-center gap-4 py-2 animate-fade-in">
            {recorder.state === 'idle' && (
              <button
                onClick={recorder.start}
                className="w-20 h-20 rounded-full bg-brand-500 hover:bg-brand-600 active:scale-95
                           flex items-center justify-center text-3xl shadow-lg shadow-brand-500/30
                           transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
                aria-label="녹음 시작"
              >
                🎙
              </button>
            )}

            {recorder.state === 'recording' && (
              <>
                <div className="relative">
                  <div className="w-20 h-20 rounded-full bg-red-500/20 animate-ping absolute inset-0" aria-hidden />
                  <button
                    onClick={recorder.stop}
                    className="relative w-20 h-20 rounded-full bg-red-500 hover:bg-red-600
                               flex items-center justify-center text-white text-xl font-bold
                               transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-red-400"
                    aria-label="녹음 중지"
                  >
                    ■
                  </button>
                </div>
                <p className="text-red-400 text-sm font-mono" aria-live="polite">
                  {String(Math.floor(recorder.durationSec / 60)).padStart(2, '0')}:
                  {String(recorder.durationSec % 60).padStart(2, '0')}
                </p>
              </>
            )}

            {recorder.state === 'stopped' && recorder.audioUrl && (
              <div className="w-full flex flex-col gap-3 animate-slide-up">
                <audio controls src={recorder.audioUrl} className="w-full h-10 accent-brand-500" aria-label="녹음된 음성" />
                <div className="flex gap-2">
                  <Button variant="ghost" onClick={recorder.reset} className="flex-1">
                    다시 녹음
                  </Button>
                  <Button onClick={handleSaveAudio} isLoading={isSaving} className="flex-1">
                    저장하기
                  </Button>
                </div>
              </div>
            )}

            {recorder.state === 'idle' && (
              <p className="text-night-400 text-sm text-center">
                버튼을 눌러 혼잣말하듯 말해보세요
              </p>
            )}
          </div>
        )}
      </section>

      {/* 저장 완료 + 요약 결과 (F2) */}
      {savedRecordId && (
        <div className="bg-night-700/40 border border-night-600/50 rounded-2xl p-5 flex flex-col gap-3 animate-slide-up">
          <p className="text-brand-300 text-xs font-semibold uppercase tracking-wide">✨ 기록 완료</p>
          {summary ? (
            <>
              <p className="text-night-100 font-medium leading-snug">{summary.summaryLine}</p>
              <div className="flex flex-wrap gap-2">
                {summary.tags.map((tag) => <Tag key={tag} label={tag} />)}
              </div>
            </>
          ) : (
            <p className="text-night-400 text-sm">AI가 생각을 정리하는 중...</p>
          )}
          <button
            onClick={() => navigate(`/records/${savedRecordId}`)}
            className="text-brand-400 text-sm hover:underline text-left"
          >
            자세히 보기 →
          </button>
        </div>
      )}
    </div>
  )
}
