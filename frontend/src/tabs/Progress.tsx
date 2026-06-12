import { useEffect, useRef, useState } from 'react'
import { Trophy, Gauge, Flame, Volume2, RotateCcw, Download, Upload, Lock } from 'lucide-react'
import { api, type Progress as ProgressData, type Medals } from '../api'
import { Button, Card, playTTS, useToast } from '../ui'
import { useI18n } from '../i18n'

function Sparkline({ points }: { points: number[] }) {
  if (points.length < 2) return <p className="text-sm text-muted">—</p>
  const W = 320, H = 60, step = W / (points.length - 1)
  const xy = (p: number, i: number) => `${(i * step).toFixed(1)},${(H - (p / 100) * H).toFixed(1)}`
  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="w-full" style={{ height: 64 }}>
      <polyline points={points.map(xy).join(' ')} fill="none" stroke="var(--accent)" strokeWidth="2" />
      {points.map((p, i) => {
        const [cx, cy] = xy(p, i).split(',')
        return <circle key={i} cx={cx} cy={cy} r="2.5" fill="var(--accent)" />
      })}
    </svg>
  )
}

export default function Progress({ refreshKey }: { refreshKey: number }) {
  const toast = useToast()
  const { t } = useI18n()
  const [data, setData] = useState<ProgressData | null>(null)
  const [medals, setMedals] = useState<Medals | null>(null)

  async function load() {
    try {
      const [d, m] = await Promise.all([api.progress(), api.medals()])
      setData(d); setMedals(m)
    } catch (e: any) { toast(e.message, 'error') }
  }
  useEffect(() => { load() }, [refreshKey])

  async function reset() {
    try { await api.resetStats(); load() } catch { /* noop */ }
  }

  const fileRef = useRef<HTMLInputElement | null>(null)
  async function doExport() {
    try {
      const data = await api.exportProgress()
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url; a.download = 'tutor-progreso.json'; a.click()
      URL.revokeObjectURL(url)
    } catch (e: any) { toast(e.message, 'error') }
  }
  async function doImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) {
      try { setData(await api.importProgress(JSON.parse(await file.text()))) }
      catch { toast('Archivo inválido', 'error') }
    }
    e.target.value = ''
  }

  const kindLabel = (k: string) => t(`kind.${k}`)

  if (!data) {
    return <div className="mx-auto max-w-3xl"><Card><p className="text-sm text-muted">{t('prog.loading')}</p></Card></div>
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="flex items-center gap-3">
          <Trophy className="text-accent" />
          <div><div className="text-2xl font-extrabold">{data.stats.points}</div>
            <div className="text-xs text-muted">{t('prog.points')}</div></div>
        </Card>
        <Card className="flex items-center gap-3">
          <Gauge className="text-accent" />
          <div><div className="text-2xl font-extrabold">{t('score.level')} {data.stats.level}</div>
            <div className="text-xs text-muted">{t('prog.byPoints')}</div></div>
        </Card>
        <Card className="flex items-center gap-3">
          <Flame className="text-accent" />
          <div><div className="text-2xl font-extrabold">{data.stats.streak}</div>
            <div className="text-xs text-muted">{t('prog.streakBest')} {data.stats.best}</div></div>
        </Card>
      </div>

      {medals && (
        <Card>
          <h3 className="font-extrabold">{t('prog.medals')}</h3>
          <p className="mb-3 text-sm text-muted">{t('prog.medalsHint')}</p>
          <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
            {medals.levels.map((m) => (
              <div key={m.level} className="flex flex-col items-center gap-1.5">
                <div className="relative">
                  <img src={`/medals/medal_${m.level}.svg`} alt={m.level}
                    className={`h-16 w-16 transition ${m.earned ? '' : 'opacity-30 grayscale'}`} />
                  {!m.earned && (
                    <span className="absolute inset-0 flex items-center justify-center text-muted">
                      <Lock size={18} />
                    </span>
                  )}
                </div>
                <span className={`text-xs font-extrabold ${m.earned ? 'text-accent' : 'text-muted'}`}>{m.level}</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Card>
        <h3 className="mb-2 font-extrabold">{t('prog.activity')} ({data.total_count})</h3>
        {data.totals.length === 0
          ? <p className="text-sm text-muted">{t('prog.noActivity')}</p>
          : <div className="flex flex-col gap-2">
            {data.totals.map((it) => (
              <div key={it.kind} className="flex items-center justify-between text-sm">
                <span className="font-semibold">{kindLabel(it.kind)}</span>
                <span className="text-muted">{it.count}{it.avg_score != null && ` · ${t('prog.avg')} ${it.avg_score}/100`}</span>
              </div>
            ))}
          </div>}
      </Card>

      <Card>
        <h3 className="mb-2 font-extrabold">{t('prog.chart')}</h3>
        <Sparkline points={data.recent.filter((r) => r.score != null).map((r) => r.score as number).reverse()} />
      </Card>

      <Card>
        <h3 className="mb-2 font-extrabold">{t('prog.wordsReview')}</h3>
        {data.missed.length === 0
          ? <p className="text-sm text-muted">{t('prog.nothingYet')}</p>
          : <div className="flex flex-wrap gap-2">
            {data.missed.map((m) => (
              <button key={m.word} onClick={() => playTTS(m.word, { lang: 'en', slow: true })} translate="no"
                className="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface2 px-3 py-1 text-sm font-semibold hover:border-accent">
                <Volume2 size={14} />{m.word}<span className="text-muted">×{m.count}</span>
              </button>
            ))}
          </div>}
      </Card>

      <Card>
        <h3 className="mb-2 font-extrabold">{t('prog.recent')}</h3>
        {data.recent.length === 0
          ? <p className="text-sm text-muted">—</p>
          : <div className="flex flex-col gap-1 text-sm">
            {data.recent.map((r, i) => (
              <div key={i} className="flex items-center justify-between">
                <span>{kindLabel(r.kind)}{r.level && <span className="text-muted"> · {r.level}</span>}</span>
                <span className="text-muted">
                  {r.score != null ? `${r.score}/100` : r.correct != null ? (r.correct ? t('prog.ok') : t('prog.failed')) : ''}
                  {' · '}{r.ts.replace('T', ' ')}
                </span>
              </div>
            ))}
          </div>}
      </Card>

      <div className="flex flex-wrap gap-2">
        <Button variant="outline" onClick={doExport}><Download size={16} />{t('btn.export')}</Button>
        <Button variant="outline" onClick={() => fileRef.current?.click()}>
          <Upload size={16} />{t('btn.import')}
        </Button>
        <input ref={fileRef} type="file" accept="application/json" className="hidden" onChange={doImport} />
        <Button variant="outline" onClick={reset}><RotateCcw size={16} />{t('btn.resetScore')}</Button>
      </div>
    </div>
  )
}
