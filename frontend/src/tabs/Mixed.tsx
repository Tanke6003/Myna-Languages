import { useEffect, useState } from 'react'
import { Shuffle, Volume2, CheckCircle2, XCircle } from 'lucide-react'
import { api, type MixedItem } from '../api'
import { Button, Card, Thinking, playTTS, useToast } from '../ui'
import { useI18n } from '../i18n'
import type { TabProps } from '../App'

const norm = (s: string) => s.toLowerCase().replace(/[^a-z']/g, '').trim()

export default function Mixed({ award, active }: TabProps & { active: boolean }) {
  const toast = useToast()
  const { t } = useI18n()
  const [item, setItem] = useState<MixedItem | null>(null)
  const [selected, setSelected] = useState('')
  const [typed, setTyped] = useState('')
  const [result, setResult] = useState<{ correct: boolean } | null>(null)
  const [loading, setLoading] = useState(false)

  async function next() {
    setLoading(true); setSelected(''); setTyped(''); setResult(null)
    try {
      const it = await api.mixedNext()
      setItem(it)
      if (it.type === 'listen' && it.word) playTTS(it.word, { lang: 'en' })
    } catch (e: any) { toast(e.message, 'error') } finally { setLoading(false) }
  }
  useEffect(() => { if (active && !item) next() }, [active])

  async function check() {
    if (!item || !item.word) return
    let correct = false
    if (item.type === 'meaning') {
      if (!selected) { toast(t('vocab.pick'), 'error'); return }
      correct = selected.trim().toLowerCase() === (item.answer || '').trim().toLowerCase()
    } else {
      if (!typed.trim()) { toast(t('dict.writeFirst'), 'error'); return }
      correct = norm(typed) === norm(item.word)
    }
    setResult({ correct })
    try { await api.mixedResult(item.word, correct) } catch { /* noop */ }
    await award(correct ? 4 : 0, correct, { kind: 'vocab', words: correct ? [] : [item.word] })
  }

  if (!item) return <div className="mx-auto max-w-2xl"><Card><Thinking /></Card></div>
  if (item.empty) {
    return <div className="mx-auto max-w-2xl"><Card><p className="text-sm text-muted">{t('mixed.empty')}</p></Card></div>
  }

  function optClass(o: string) {
    if (result && o === item!.answer) return 'border-good bg-accentSoft'
    if (result && selected === o && !result.correct) return 'border-bad'
    if (selected === o) return 'border-accent bg-accentSoft'
    return 'border-line bg-surface hover:bg-surface2'
  }

  return (
    <div className="mx-auto max-w-2xl">
      <Card className="flex flex-col gap-3">
        <p className="text-sm text-muted">{t('mixed.intro')} · <b>{item.remaining}</b> {t('mixed.remaining')}.</p>

        {loading ? (
          // Cargando la siguiente palabra: indicador y bloqueo (sin opciones ni Comprobar clicables).
          <div className="flex items-center justify-center rounded-xl bg-surface2 p-8"><Thinking /></div>
        ) : (
          <>
            {item.type === 'meaning' ? (
              <>
                <div className="rounded-xl bg-surface2 p-4 text-center">
                  <button onClick={() => playTTS(item.word!, { lang: 'en' })}
                    className="inline-flex items-center gap-2 text-2xl font-extrabold hover:text-accent" translate="no">
                    <Volume2 size={18} />{item.word}
                  </button>
                </div>
                <div className="flex flex-col gap-2">
                  {item.options!.map((o) => (
                    <button key={o} onClick={() => !result && setSelected(o)}
                      className={`rounded-xl border px-3 py-2.5 text-left text-sm font-semibold transition ${optClass(o)}`}>
                      {o}
                    </button>
                  ))}
                </div>
              </>
            ) : (
              <>
                <div className="flex items-center justify-center gap-2 rounded-xl bg-surface2 p-4">
                  <Button variant="outline" onClick={() => playTTS(item.word!, { lang: 'en' })}>
                    <Volume2 size={16} />{t('btn.repeat')}
                  </Button>
                  <Button variant="outline" onClick={() => playTTS(item.word!, { lang: 'en', slow: true })}>
                    <Volume2 size={16} />{t('btn.slow')}
                  </Button>
                </div>
                <label className="text-sm font-semibold text-muted">{t('mixed.listenPrompt')}</label>
                <input value={typed} onChange={(e) => setTyped(e.target.value)} translate="no"
                  onKeyDown={(e) => e.key === 'Enter' && !result && check()}
                  className="rounded-xl border border-line bg-surface px-3 py-2.5 text-sm" />
              </>
            )}

            {!result
              ? <Button onClick={check}><CheckCircle2 size={16} />{t('btn.check')}</Button>
              : (
                <>
                  <div className="rounded-xl border border-line p-3 text-sm">
                    <div className={`flex items-center gap-1.5 font-extrabold ${result.correct ? 'text-good' : 'text-bad'}`}>
                      {result.correct ? <CheckCircle2 size={18} /> : <XCircle size={18} />}
                      {result.correct
                        ? t('vocab.correct')
                        : <span translate="no">{item.type === 'listen' ? item.word : `${t('vocab.answer')} ${item.answer}`}</span>}
                    </div>
                    {item.explain && <p className="mt-1 text-muted">{item.explain}</p>}
                  </div>
                  <Button onClick={next}><Shuffle size={16} />{t('mixed.next')}</Button>
                </>
              )}
          </>
        )}
      </Card>
    </div>
  )
}
