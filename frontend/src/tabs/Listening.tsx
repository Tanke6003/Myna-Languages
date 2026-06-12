import { useState } from 'react'
import { Ear, Volume2, CheckCircle2, XCircle } from 'lucide-react'
import { api, type ListeningExercise } from '../api'
import { Button, Card, Thinking, SpeedControl, playTTS, useToast } from '../ui'
import { useI18n } from '../i18n'
import type { TabProps } from '../App'

export default function Listening({ level, award }: TabProps) {
  const toast = useToast()
  const { t } = useI18n()
  const [ex, setEx] = useState<ListeningExercise | null>(null)
  const [selected, setSelected] = useState('')
  const [result, setResult] = useState<{ correct: boolean } | null>(null)
  const [loading, setLoading] = useState(false)

  async function newEx() {
    setLoading(true)
    try {
      const e = await api.listeningNew(level)
      setEx(e); setSelected(''); setResult(null)
      playTTS(e.passage, { lang: 'en' })
    } catch (err: any) { toast(err.message, 'error') } finally { setLoading(false) }
  }

  function check() {
    if (!ex || !selected) { toast(t('vocab.pick'), 'error'); return }
    const correct = selected.trim().toLowerCase() === ex.answer.trim().toLowerCase()
    setResult({ correct })
    award(correct ? 5 : 0, correct, { kind: 'listening', level })
  }

  function optClass(o: string) {
    if (result && o === ex!.answer) return 'border-good bg-accentSoft'
    if (result && selected === o && !result.correct) return 'border-bad'
    if (selected === o) return 'border-accent bg-accentSoft'
    return 'border-line bg-surface hover:bg-surface2'
  }

  return (
    <div className="mx-auto max-w-2xl">
      <Card className="flex flex-col gap-3">
        <p className="text-sm text-muted">{t('listening.intro')}</p>
        <div className="flex flex-wrap gap-2">
          <Button onClick={newEx} loading={loading}><Ear size={16} />{t('btn.newExercise')}</Button>
          {ex && (
            <>
              <Button variant="outline" onClick={() => playTTS(ex.passage, { lang: 'en' })}>
                <Volume2 size={16} />{t('btn.repeat')}
              </Button>
              <Button variant="outline" onClick={() => playTTS(ex.passage, { lang: 'en', slow: true })}>
                <Volume2 size={16} />{t('btn.slow')}
              </Button>
              <SpeedControl />
            </>
          )}
        </div>

        {loading && <div className="rounded-xl bg-surface2 p-4"><Thinking /></div>}

        {ex && !loading && (
          <div className="flex flex-col gap-3">
            <div className="text-base font-bold" translate="no">{ex.question}</div>
            <div className="flex flex-col gap-2" translate="no">
              {ex.options.map((o) => (
                <button key={o} onClick={() => !result && setSelected(o)}
                  className={`rounded-xl border px-3 py-2.5 text-left text-sm font-semibold transition ${optClass(o)}`}>
                  {o}
                </button>
              ))}
            </div>
            <Button onClick={check} disabled={!selected || !!result}><CheckCircle2 size={16} />{t('btn.check')}</Button>
            {result && (
              <div className="rounded-xl border border-line p-3 text-sm">
                <div className={`flex items-center gap-1.5 font-extrabold ${result.correct ? 'text-good' : 'text-bad'}`}>
                  {result.correct ? <CheckCircle2 size={18} /> : <XCircle size={18} />}
                  {result.correct ? t('vocab.correct') : <span>{t('vocab.answer')} <span translate="no">{ex.answer}</span></span>}
                </div>
                <p className="mt-1" translate="no"><b>{t('listening.passage')}:</b> {ex.passage}</p>
                {ex.explain && <p className="mt-1 text-muted">{ex.explain}</p>}
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  )
}
