import { useState } from 'react'
import { AudioLines, Volume2, CheckCircle2, XCircle } from 'lucide-react'
import { api, type MinimalExercise } from '../api'
import { Button, Card, Thinking, SpeedControl, ReportRepeat, playTTS, useToast } from '../ui'
import { useI18n } from '../i18n'
import type { TabProps } from '../App'

export default function MinimalPairs({ level, award }: TabProps) {
  const toast = useToast()
  const { t } = useI18n()
  const [ex, setEx] = useState<MinimalExercise | null>(null)
  const [selected, setSelected] = useState('')
  const [result, setResult] = useState<{ correct: boolean } | null>(null)
  const [loading, setLoading] = useState(false)

  async function newEx() {
    setLoading(true)
    try {
      const e = await api.minimalNew(level)
      setEx(e); setSelected(''); setResult(null)
      playTTS(e.word, { lang: 'en' })
    } catch (err: any) { toast(err.message, 'error') } finally { setLoading(false) }
  }

  function check() {
    if (!ex || !selected) { toast(t('vocab.pick'), 'error'); return }
    const correct = selected.trim().toLowerCase() === ex.answer.trim().toLowerCase()
    setResult({ correct })
    award(correct ? 5 : 0, correct, { kind: 'minimal', level, score: correct ? 100 : 0 })
  }

  function optClass(o: string) {
    if (result && o.toLowerCase() === ex!.answer.toLowerCase()) return 'border-good bg-accentSoft'
    if (result && selected === o && !result.correct) return 'border-bad'
    if (selected === o) return 'border-accent bg-accentSoft'
    return 'border-line bg-surface hover:bg-surface2'
  }

  return (
    <div className="mx-auto max-w-2xl">
      <Card className="flex flex-col gap-3">
        <p className="text-sm text-muted">{t('minimal.intro')}</p>
        <div className="flex flex-wrap items-center gap-2">
          <Button onClick={newEx} loading={loading}><AudioLines size={16} />{t('minimal.new')}</Button>
          {ex && (
            <>
              <Button variant="outline" onClick={() => playTTS(ex.word, { lang: 'en' })}>
                <Volume2 size={16} />{t('btn.repeat')}
              </Button>
              <Button variant="outline" onClick={() => playTTS(ex.word, { lang: 'en', slow: true })}>
                <Volume2 size={16} />{t('btn.slow')}
              </Button>
              <SpeedControl />
              <ReportRepeat onReport={newEx} loading={loading} className="ml-auto self-center" />
            </>
          )}
        </div>

        {loading && <div className="rounded-xl bg-surface2 p-4"><Thinking /></div>}
        {!ex && !loading && <p className="text-sm text-muted">{t('minimal.startHint')}</p>}

        {ex && !loading && (
          <div className="flex flex-col gap-3">
            {/* Botón grande para volver a oír la palabra */}
            <button onClick={() => playTTS(ex.word, { lang: 'en' })}
              className="flex items-center justify-center gap-2 rounded-2xl border border-line bg-surface2 p-6 text-accent transition hover:bg-surface">
              <Volume2 size={28} /><span className="text-sm font-bold text-muted">{t('btn.listen')}</span>
            </button>

            <div className="flex flex-col gap-2" translate="no">
              {ex.options.map((o) => (
                <button key={o} onClick={() => !result && setSelected(o)}
                  className={`flex items-center justify-between rounded-xl border px-3 py-2.5 text-left text-sm font-semibold transition ${optClass(o)}`}>
                  <span>{o}</span>
                  {result && ex.ipa[o] && <span className="font-mono text-xs text-muted">{ex.ipa[o]}</span>}
                </button>
              ))}
            </div>

            {!result && (
              <Button onClick={check} disabled={!selected}><CheckCircle2 size={16} />{t('btn.check')}</Button>
            )}

            {result && (
              <div className="rounded-xl border border-line p-3 text-sm">
                <div className={`flex items-center gap-1.5 font-extrabold ${result.correct ? 'text-good' : 'text-bad'}`}>
                  {result.correct ? <CheckCircle2 size={18} /> : <XCircle size={18} />}
                  {result.correct ? t('vocab.correct')
                    : <span>{t('vocab.answer')} <span translate="no">{ex.answer}</span></span>}
                </div>
                {ex.explain && <p className="mt-1 text-muted">{ex.explain}</p>}
                <p className="mt-2 text-xs font-semibold text-muted">{t('minimal.compare')}</p>
                <div className="mt-1 flex flex-wrap gap-2" translate="no">
                  {ex.options.map((o) => (
                    <button key={o} onClick={() => playTTS(o, { lang: 'en' })}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-line bg-surface px-2.5 py-1.5 text-sm font-semibold hover:bg-surface2">
                      <Volume2 size={14} />{o}
                      {ex.ipa[o] && <span className="font-mono text-xs text-muted">{ex.ipa[o]}</span>}
                    </button>
                  ))}
                </div>
                <Button variant="outline" className="mt-3" onClick={newEx} loading={loading}>
                  <AudioLines size={16} />{t('minimal.new')}
                </Button>
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  )
}
