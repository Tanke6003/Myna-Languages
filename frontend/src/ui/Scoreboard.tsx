import { Trophy, Gauge, Flame } from 'lucide-react'
import { type Stats } from '../api'
import { useI18n } from '../i18n'
import { Pill } from './primitives'

export function Scoreboard({ stats }: { stats: Stats | null }) {
  const { t } = useI18n()
  if (!stats) return null
  const into = stats.points % 100
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-line bg-surface px-4 py-2.5 shadow-soft">
      <Pill><Trophy size={15} className="text-accent" /> {stats.points} pts</Pill>
      <Pill><Gauge size={15} className="text-accent" /> {t('score.level')} {stats.level}</Pill>
      <div className="h-2 w-28 overflow-hidden rounded-full bg-surface2" title={`${into}/100`}>
        <div className="h-full rounded-full bg-accent transition-all duration-500" style={{ width: `${into}%` }} />
      </div>
      <Pill><Flame size={15} className="text-accent" /> {stats.streak}
        <span className="font-normal text-muted">· {t('score.record')} {stats.best}</span></Pill>
    </div>
  )
}
