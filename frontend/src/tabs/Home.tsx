import { useEffect, useState } from 'react'
import { GraduationCap, Mic, Layers, Shuffle, TrendingUp, ArrowRight } from 'lucide-react'
import { api, type HomeData } from '../api'
import { Button } from '../ui'
import { MODULES, CATEGORIES } from '../modules'
import { useI18n } from '../i18n'

interface Props {
  onOpen: (id: string) => void
  onLevelUp: () => void
  level: string
  refreshKey: number
}

export default function Home({ onOpen, onLevelUp, level, refreshKey }: Props) {
  const { t } = useI18n()
  const [data, setData] = useState<HomeData | null>(null)
  useEffect(() => { api.home(level).then(setData).catch(() => {}) }, [level, refreshKey])

  const recs: { Icon: typeof Mic; text: string; btn?: string; action?: () => void }[] = []
  if (data) {
    const lu = data.levelup
    if (lu.ready && lu.next_level) {
      recs.push({ Icon: GraduationCap, text: `${t('levelup.msg')} ${lu.next_level}?`, btn: `${t('levelup.up')} ${lu.next_level}`, action: onLevelUp })
    }
    if (data.total_activity === 0) {
      recs.push({ Icon: Mic, text: t('rec.start'), btn: t('rec.go'), action: () => onOpen('conv') })
    }
    if (data.flashcards_due > 0) {
      recs.push({ Icon: Layers, text: `${data.flashcards_due} ${t('rec.flashcardsDue')}`, btn: t('rec.review'), action: () => onOpen('flashcards') })
    }
    if (data.missed_count > 0) {
      recs.push({ Icon: Shuffle, text: `${data.missed_count} ${t('rec.missedWords')}: ${data.missed.slice(0, 5).map((m) => m.word).join(', ')}`, btn: t('rec.review'), action: () => onOpen('mixed') })
    }
    if (!lu.ready && data.total_activity > 0 && lu.next_level) {
      recs.push({ Icon: TrendingUp, text: `${t('rec.progressTo')} ${lu.next_level}: ${lu.count}/${lu.need} · ${lu.avg_score || 0}/85` })
    }
  }
  const shown = recs.slice(0, 3)

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-2xl font-extrabold">{t('home.title')}</h2>
        <p className="text-muted">{t('home.subtitle')}</p>
      </div>

      {shown.length > 0 && (
        <div>
          <div className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">{t('rec.title')}</div>
          <div className="flex flex-col gap-2">
            {shown.map((r, i) => (
              <div key={i} className="flex flex-wrap items-center gap-3 rounded-2xl border border-line bg-accentSoft p-3">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-accent text-accentFg">
                  <r.Icon size={18} />
                </span>
                <span className="flex-1 text-sm font-semibold">{r.text}</span>
                {r.btn && r.action && (
                  <Button onClick={r.action}>{r.btn}<ArrowRight size={15} /></Button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {CATEGORIES.map((cat) => (
        <div key={cat}>
          <div className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">{t('cat.' + cat)}</div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {MODULES.filter((m) => m.cat === cat).map((m) => (
              <button key={m.id} onClick={() => onOpen(m.id)}
                className="flex flex-col gap-2 rounded-2xl border border-line bg-surface p-4 text-left shadow-soft transition hover:-translate-y-0.5 hover:border-accent">
                <div className="flex items-center gap-2">
                  <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-accentSoft text-accent">
                    <m.Icon size={18} />
                  </span>
                  <span className="font-extrabold">{t('nav.' + m.id)}</span>
                </div>
                <p className="text-sm text-muted">{t('mod.' + m.id + '.desc')}</p>
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
