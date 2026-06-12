import { useState } from 'react'
import { Dices, CheckCircle2, XCircle } from 'lucide-react'
import { api, type VocabExercise } from '../api'
import { Button, Card, HintToggle, useToast } from '../ui'
import { useI18n } from '../i18n'
import type { TabProps } from '../App'

type Kind = 'tense' | 'synonym' | 'antonym' | 'preposition' | 'phrasal'
const KINDS: { k: Kind; key: string }[] = [
  { k: 'tense', key: 'vocab.tense' },
  { k: 'synonym', key: 'vocab.synonym' },
  { k: 'antonym', key: 'vocab.antonym' },
  { k: 'preposition', key: 'vocab.preposition' },
  { k: 'phrasal', key: 'vocab.phrasal' },
]

export default function Vocabulary({ level, award }: TabProps) {
  const toast = useToast()
  const { t } = useI18n()
  const [kind, setKind] = useState<Kind>('tense')
  const [ex, setEx] = useState<VocabExercise | null>(null)
  const [selected, setSelected] = useState('')
  const [result, setResult] = useState<{ correct: boolean } | null>(null)
  const [loadingNew, setLoadingNew] = useState(false)

  async function newEx() {
    setLoadingNew(true)
    try {
      const e = await api.vocabNew(level, kind)
      setEx(e); setSelected(''); setResult(null)
    } catch (err: any) { toast(err.message, 'error') } finally { setLoadingNew(false) }
  }

  async function check() {
    if (!ex || !selected) { toast(t('vocab.pick'), 'error'); return }
    const correct = selected.trim().toLowerCase() === ex.answer.trim().toLowerCase()
    setResult({ correct })
    await award(correct ? 5 : 0, correct, { kind: 'vocab', level })
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
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="inline-flex flex-wrap gap-1 rounded-xl bg-surface2 p-1">
            {KINDS.map(({ k, key }) => (
              <button key={k} onClick={() => setKind(k)}
                className={`rounded-lg px-3 py-1.5 text-sm font-bold transition ${
                  kind === k ? 'bg-surface text-accent shadow-soft' : 'text-muted hover:text-text'}`}>
                {t(key)}
              </button>
            ))}
          </div>
          <Button onClick={newEx} loading={loadingNew}><Dices size={16} />{t('btn.newExercise')}</Button>
        </div>
        {!ex && <p className="text-sm text-muted">{t('vocab.startHint')}</p>}
        {ex && (
          <div className="flex flex-col gap-3">
            <div className="text-sm text-muted" translate="no">{ex.question}</div>
            <div className="rounded-xl bg-surface2 p-4 text-lg font-bold" translate="no">{ex.prompt}</div>
            <HintToggle text={ex.prompt} />
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
                  {result.correct ? t('vocab.correct')
                    : <span>{t('vocab.answer')} <span translate="no">{ex.answer}</span></span>}
                </div>
                {ex.explain && <p className="mt-1 text-muted">{ex.explain}</p>}
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  )
}
