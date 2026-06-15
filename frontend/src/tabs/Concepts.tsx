import { useEffect, useState } from 'react'
import { Plus, Trash2, Dices, CheckCircle2, XCircle, Volume2 } from 'lucide-react'
import { api, type ConceptsState, type ConceptExercise, type ConceptCheck } from '../api'
import { Button, Card, HintToggle, Thinking, ReportRepeat, playTTS, useToast } from '../ui'
import { useI18n } from '../i18n'
import type { TabProps } from '../App'

const norm = (s: string) => s.trim().toLowerCase().replace(/\s+/g, ' ').replace(/[.,!?;:'"]/g, '')

export default function Concepts({ level, award }: TabProps) {
  const toast = useToast()
  const { t } = useI18n()
  const [state, setState] = useState<ConceptsState | null>(null)
  const [phrase, setPhrase] = useState('')
  const [example, setExample] = useState('')
  const [busy, setBusy] = useState(false)

  const [ex, setEx] = useState<ConceptExercise | null>(null)
  const [loadingEx, setLoadingEx] = useState(false)
  const [typed, setTyped] = useState('')
  const [selected, setSelected] = useState('')
  const [sentence, setSentence] = useState('')
  const [result, setResult] = useState<{ correct: boolean } | null>(null)
  const [check, setCheck] = useState<ConceptCheck | null>(null)

  async function load() {
    try { setState(await api.concepts()) } catch (e: any) { toast(e.message, 'error') }
  }
  useEffect(() => { load() }, [])

  async function add() {
    if (!phrase.trim()) return
    setBusy(true)
    try {
      setState(await api.conceptAdd(phrase.trim(), example.trim()))
      setPhrase(''); setExample(''); toast(t('concepts.added'), 'success')
    } catch (e: any) { toast(e.message, 'error') } finally { setBusy(false) }
  }
  async function del(id: number) {
    try { setState(await api.conceptDelete(id)) } catch (e: any) { toast(e.message, 'error') }
  }

  function resetAnswer() { setTyped(''); setSelected(''); setSentence(''); setResult(null); setCheck(null) }

  async function practice() {
    setLoadingEx(true); resetAnswer()
    try {
      const e = await api.conceptPractice(level)
      if (e.empty) { setEx(null); toast(t('concepts.empty'), 'error') } else { setEx(e) }
    } catch (err: any) { toast(err.message, 'error') } finally { setLoadingEx(false) }
  }

  async function checkGap() {
    if (!ex || !typed.trim() || result) return
    const correct = norm(typed) === norm(ex.answer || '')
    setResult({ correct })
    await award(correct ? 5 : 0, correct, { kind: 'concept', level, score: correct ? 100 : 0 })
  }
  async function checkChoice() {
    if (!ex || !selected || result) return
    const correct = norm(selected) === norm(ex.answer || '')
    setResult({ correct })
    await award(correct ? 5 : 0, correct, { kind: 'concept', level, score: correct ? 100 : 0 })
  }
  async function checkProduce() {
    if (!ex || !sentence.trim() || check) return
    setBusy(true)
    try {
      const r = await api.conceptCheck(ex.phrase || '', sentence.trim())
      setCheck(r)
      await award(r.correct ? 7 : 0, r.correct, { kind: 'concept', level, score: r.correct ? 100 : 0 })
    } catch (err: any) { toast(err.message, 'error') } finally { setBusy(false) }
  }

  function optClass(o: string) {
    if (result && norm(o) === norm(ex!.answer || '')) return 'border-good bg-accentSoft'
    if (result && selected === o && !result.correct) return 'border-bad'
    if (selected === o) return 'border-accent bg-accentSoft'
    return 'border-line bg-surface hover:bg-surface2'
  }

  const answered = !!result || !!check

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4">
      {/* Práctica */}
      <Card className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm text-muted">{t('concepts.help')}</p>
        </div>
        <div className="flex items-center justify-between gap-2">
          <Button onClick={practice} loading={loadingEx} disabled={!state?.count}>
            <Dices size={16} />{t('concepts.practice')}
          </Button>
          {ex && !loadingEx && ex.type !== 'produce' && <ReportRepeat onReport={practice} loading={loadingEx} />}
        </div>

        {loadingEx && <div className="rounded-xl bg-surface2 p-4"><Thinking /></div>}
        {!ex && !loadingEx && <p className="text-sm text-muted">{t('concepts.startHint')}</p>}

        {ex && !loadingEx && (
          <div className="flex flex-col gap-3">
            {/* GAP: rellenar el hueco */}
            {ex.type === 'gap' && (
              <>
                <div className="rounded-xl bg-surface2 p-4 text-lg font-bold" translate="no">{ex.prompt}</div>
                <HintToggle text={ex.prompt || ''} />
                <label className="text-sm font-semibold text-muted">{t('concepts.gapLabel')}</label>
                <input value={typed} onChange={(e) => setTyped(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && checkGap()} placeholder={t('concepts.gapPh')}
                  translate="no" disabled={!!result}
                  className="rounded-xl border border-line bg-surface px-3 py-2.5 text-sm" />
                <Button onClick={checkGap} disabled={!typed.trim() || !!result}>
                  <CheckCircle2 size={16} />{t('btn.check')}
                </Button>
              </>
            )}

            {/* CHOICE: opción múltiple */}
            {ex.type === 'choice' && (
              <>
                <div className="text-sm text-muted" translate="no">{ex.question}</div>
                <div className="rounded-xl bg-surface2 p-4 text-lg font-bold" translate="no">{ex.prompt}</div>
                <div className="flex flex-col gap-2" translate="no">
                  {(ex.options || []).map((o) => (
                    <button key={o} onClick={() => !result && setSelected(o)}
                      className={`rounded-xl border px-3 py-2.5 text-left text-sm font-semibold transition ${optClass(o)}`}>
                      {o}
                    </button>
                  ))}
                </div>
                <Button onClick={checkChoice} disabled={!selected || !!result}>
                  <CheckCircle2 size={16} />{t('btn.check')}
                </Button>
              </>
            )}

            {/* PRODUCE: escribe tu propia frase */}
            {ex.type === 'produce' && (
              <>
                <div className="flex items-center justify-between rounded-xl bg-surface2 p-4">
                  <button onClick={() => playTTS(ex.phrase || '', { lang: 'en' })}
                    className="inline-flex items-center gap-2 text-lg font-extrabold hover:text-accent" translate="no">
                    <Volume2 size={16} />{ex.phrase}
                  </button>
                  {ex.meaning && <span className="text-sm text-muted">{ex.meaning}</span>}
                </div>
                <label className="text-sm font-semibold text-muted">{t('concepts.produceLabel')}</label>
                <textarea value={sentence} onChange={(e) => setSentence(e.target.value)}
                  placeholder={t('concepts.producePh')} translate="no" rows={2} disabled={!!check}
                  className="rounded-xl border border-line bg-surface px-3 py-2.5 text-sm" />
                <Button onClick={checkProduce} loading={busy} disabled={!sentence.trim() || !!check}>
                  <CheckCircle2 size={16} />{t('btn.check')}
                </Button>
              </>
            )}

            {/* Resultado de gap / choice */}
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

            {/* Resultado de produce */}
            {check && (
              <div className="rounded-xl border border-line p-3 text-sm">
                <div className={`flex items-center gap-1.5 font-extrabold ${check.correct ? 'text-good' : 'text-bad'}`}>
                  {check.correct ? <CheckCircle2 size={18} /> : <XCircle size={18} />}
                  {check.correct ? t('vocab.correct') : t('concepts.incorrect')}
                </div>
                {check.better && (
                  <p className="mt-1" translate="no"><b>{t('concepts.better')}</b> {check.better}</p>
                )}
                {check.feedback && <p className="mt-1 text-muted">{check.feedback}</p>}
              </div>
            )}

            {answered && (
              <Button variant="outline" onClick={practice} loading={loadingEx}>
                <Dices size={16} />{t('btn.newExercise')}
              </Button>
            )}
          </div>
        )}
      </Card>

      {/* Mi lista de expresiones */}
      <Card className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <b className="text-sm">{t('concepts.listTitle')}</b>
          <span className="text-sm text-muted">{state?.count ?? 0}</span>
        </div>
        <div className="flex flex-col gap-2">
          <input value={phrase} onChange={(e) => setPhrase(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && add()} placeholder={t('concepts.addPlaceholder')}
            translate="no" className="rounded-xl border border-line bg-surface px-3 py-2.5 text-sm" />
          <div className="flex gap-2">
            <input value={example} onChange={(e) => setExample(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && add()} placeholder={t('concepts.examplePh')}
              translate="no" className="flex-1 rounded-xl border border-line bg-surface px-3 py-2.5 text-sm" />
            <Button onClick={add} loading={busy}><Plus size={16} />{t('concepts.add')}</Button>
          </div>
        </div>

        {!state?.items.length ? (
          <p className="rounded-xl border border-dashed border-line p-4 text-center text-sm text-muted">
            {t('concepts.empty')}
          </p>
        ) : (
          <ul className="flex flex-col gap-2">
            {state.items.map((c) => (
              <li key={c.id} className="flex items-start justify-between gap-2 rounded-xl border border-line p-3">
                <div className="min-w-0">
                  <button onClick={() => playTTS(c.phrase, { lang: 'en' })}
                    className="inline-flex items-center gap-1.5 font-bold hover:text-accent" translate="no">
                    <Volume2 size={14} />{c.phrase}
                  </button>
                  {c.meaning && <div className="text-sm text-muted">{c.meaning}</div>}
                  {c.example && <div className="mt-0.5 text-xs italic text-muted" translate="no">“{c.example}”</div>}
                </div>
                <button onClick={() => del(c.id)} title={t('concepts.deleteTitle')}
                  className="shrink-0 rounded-lg p-1.5 text-muted transition hover:bg-surface2 hover:text-bad">
                  <Trash2 size={16} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}
