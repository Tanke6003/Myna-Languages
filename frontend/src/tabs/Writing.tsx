import { useState } from 'react'
import { Dices, CheckCircle2, XCircle } from 'lucide-react'
import { api, type WritingExercise, type WritingCheck } from '../api'
import { Button, Card, Thinking, ReportRepeat, useToast } from '../ui'
import { useI18n } from '../i18n'
import type { TabProps } from '../App'

type Kind = 'rewrite' | 'translate' | 'complete' | 'paragraph'
const KINDS: Kind[] = ['rewrite', 'translate', 'complete', 'paragraph']

export default function Writing({ level, award }: TabProps) {
  const toast = useToast()
  const { t } = useI18n()
  const [kind, setKind] = useState<Kind>('rewrite')
  const [ex, setEx] = useState<WritingExercise | null>(null)
  const [answer, setAnswer] = useState('')
  const [result, setResult] = useState<WritingCheck | null>(null)
  const [loadingNew, setLoadingNew] = useState(false)
  const [loadingCheck, setLoadingCheck] = useState(false)

  async function newEx() {
    setLoadingNew(true)
    try {
      const e = await api.writingNew(level, kind)
      setEx(e); setResult(null)
      // 'complete': el alumno continúa la frase, así que pre-rellenamos con el principio.
      setAnswer(e.kind === 'complete' ? e.prompt + ' ' : '')
    } catch (err: any) { toast(err.message, 'error') } finally { setLoadingNew(false) }
  }

  async function check() {
    if (!ex) { toast(t('writing.genFirst'), 'error'); return }
    if (!answer.trim()) { toast(t('writing.writeFirst'), 'error'); return }
    setLoadingCheck(true)
    try {
      const r = await api.writingCheck(ex.kind, ex.prompt, ex.instruction, answer, level)
      setResult(r)
      const score = r.score ?? (r.correct ? 100 : 0)
      await award(r.correct ? 10 : 0, r.correct, { kind: 'writing', level, score })
    } catch (err: any) { toast(err.message, 'error') } finally { setLoadingCheck(false) }
  }

  function pickKind(k: Kind) {
    setKind(k); setEx(null); setResult(null); setAnswer('')
  }

  return (
    <div className="mx-auto max-w-2xl">
      <Card className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="inline-flex flex-wrap gap-1 rounded-xl bg-surface2 p-1">
            {KINDS.map((k) => (
              <button key={k} onClick={() => pickKind(k)}
                className={`rounded-lg px-3 py-1.5 text-sm font-bold transition ${
                  kind === k ? 'bg-surface text-accent shadow-soft' : 'text-muted hover:text-text'}`}>
                {t('writing.' + k)}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-3">
            {ex && !loadingNew && <ReportRepeat onReport={newEx} loading={loadingNew} />}
            <Button onClick={newEx} loading={loadingNew}><Dices size={16} />{t('btn.newExercise')}</Button>
          </div>
        </div>

        {loadingNew && <div className="rounded-xl bg-surface2 p-4"><Thinking /></div>}
        {!ex && !loadingNew && <p className="text-sm text-muted">{t('writing.startHint')}</p>}

        {ex && !loadingNew && (
          <div className="flex flex-col gap-3">
            <div className="text-sm font-semibold text-muted">{t('writing.' + ex.kind + 'Label')}</div>

            {/* Enunciado (en 'complete' va dentro del textarea, no se repite aquí) */}
            {ex.kind !== 'complete' && (
              <div className="rounded-xl bg-surface2 p-4 text-lg font-bold" translate="no">{ex.prompt}</div>
            )}
            {ex.kind === 'rewrite' && ex.instruction && (
              <div className="rounded-xl border border-accent bg-accentSoft p-3 text-sm font-semibold">
                {ex.instruction}
              </div>
            )}

            <textarea value={answer} onChange={(e) => setAnswer(e.target.value)}
              rows={ex.kind === 'paragraph' ? 4 : 2} placeholder={t('writing.placeholder')} translate="no"
              className="rounded-xl border border-line bg-surface px-3 py-2.5 text-sm" />

            <Button onClick={check} loading={loadingCheck} disabled={!answer.trim()}>
              <CheckCircle2 size={16} />{t('btn.check')}
            </Button>

            {loadingCheck && <div className="rounded-xl border border-line p-3"><Thinking /></div>}

            {result && !loadingCheck && (
              <div className="rounded-xl border border-line p-3 text-sm">
                <div className="flex items-center justify-between">
                  <div className={`flex items-center gap-1.5 font-extrabold ${result.correct ? 'text-good' : 'text-bad'}`}>
                    {result.correct ? <CheckCircle2 size={18} /> : <XCircle size={18} />}
                    {result.correct ? t('vocab.correct') : t('concepts.incorrect')}
                  </div>
                  {typeof result.score === 'number' && (
                    <span className="text-xs font-bold text-muted">
                      {t('writing.score')}: <span className="text-accent">{result.score}</span>/100
                    </span>
                  )}
                </div>
                {result.better && <p className="mt-2" translate="no"><b>{t('concepts.better')}</b> {result.better}</p>}
                {result.feedback && <p className="mt-1 text-muted">{result.feedback}</p>}
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  )
}
