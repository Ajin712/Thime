import { clsx } from 'clsx'

interface TagProps {
  label: string
  className?: string
}

export function Tag({ label, className }: TagProps) {
  return (
    <span
      className={clsx(
        'inline-block text-xs font-medium px-2.5 py-1 rounded-full',
        'bg-brand-500/15 text-brand-300 border border-brand-500/20',
        className,
      )}
    >
      {label}
    </span>
  )
}
