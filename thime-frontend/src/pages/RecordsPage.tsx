/**
 * 기록 목록 — F3 다시 만나기 흐름
 */
import { Link } from 'react-router-dom'
import { useRecordList } from '@/hooks/useRecords'
import { Tag } from '@/components/ui/Tag'
import { clsx } from 'clsx'
import dayjs from 'dayjs'

export function RecordsPage() {
  const { data, isLoading, isError } = useRecordList()

  if (isLoading) return <LoadingSkeleton />
  if (isError)   return <p className="text-red-400 text-sm">기록을 불러오지 못했습니다.</p>

  const records = data?.records ?? []

  return (
    <div className="flex flex-col gap-5 animate-fade-in">
      <h2 className="text-xl font-bold">내 기록</h2>

      {records.length === 0 && (
        <div className="text-center py-16 text-night-400">
          <p className="text-4xl mb-3">🌙</p>
          <p className="text-sm">아직 기록이 없어요.<br />오늘 밤 생각을 남겨보세요.</p>
        </div>
      )}

      <ul className="flex flex-col gap-3">
        {records.map((record) => {
          // F3: 2~3주 전 기록에 "다시 만나기" 뱃지
          const daysDiff = dayjs().diff(dayjs(record.createdAt), 'day')
          const isRecall = daysDiff >= 14 && daysDiff <= 21

          return (
            <li key={record.recordId}>
              <Link
                to={`/records/${record.recordId}`}
                className={clsx(
                  'block bg-night-700/40 border rounded-2xl p-4 transition-colors hover:bg-night-700/70',
                  isRecall ? 'border-brand-500/40' : 'border-night-600/50',
                )}
              >
                {isRecall && (
                  <p className="text-brand-300 text-xs font-semibold mb-2 flex items-center gap-1">
                    <span>✨</span> 2~3주 전 생각이에요. 지금은 어떻게 생각하나요?
                  </p>
                )}
                <p className="text-night-100 font-medium text-sm leading-relaxed line-clamp-2">
                  {record.summaryLine || record.rawText || '처리 중...'}
                </p>
                <div className="flex items-center justify-between mt-3">
                  <div className="flex flex-wrap gap-1.5">
                    {record.tags.map((tag) => <Tag key={tag} label={tag} />)}
                  </div>
                  <time className="text-night-500 text-xs" dateTime={record.createdAt}>
                    {dayjs(record.createdAt).format('M/D')}
                  </time>
                </div>
                {record.followups?.length > 0 && (
                  <p className="text-night-500 text-xs mt-2">
                    💭 이어 생각 {record.followups.length}개
                  </p>
                )}
              </Link>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div className="flex flex-col gap-3" aria-busy aria-label="기록 불러오는 중">
      {[...Array(4)].map((_, i) => (
        <div key={i} className="bg-night-700/40 border border-night-600/50 rounded-2xl p-4 animate-pulse">
          <div className="h-4 bg-night-600 rounded w-3/4 mb-2" />
          <div className="h-3 bg-night-600 rounded w-1/2" />
        </div>
      ))}
    </div>
  )
}
