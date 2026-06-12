import { useState } from 'react'
import { Languages, Pencil, RefreshCw, X, Volume2 } from 'lucide-react'
import { api, type TranslationDetails } from '../api'
import { Button, Card, Segmented, Spinner, TtsButton, playTTS, useToast } from '../ui'
import { useI18n } from '../i18n'
import type { TabProps } from '../App'

function isSpanish(s: string) {
  return /[áéíóúñ¿¡]/i.test(s) || /\b(el|la|los|las|que|para|con|una|un|de|por|pero)\b/i.test(s)
}

export default function Translator(_props: TabProps) {
  const toast = useToast()
  const { t } = useI18n()
  const [text, setText] = useState('')
  const [direction, setDirection] = useState('Auto')
  const [output, setOutput] = useState('')
  const [loading, setLoading] = useState(false)
  const [noteOpen, setNoteOpen] = useState(false)
  const [note, setNote] = useState('')
  const [details, setDetails] = useState<TranslationDetails | null>(null)
  const [detailsLoading, setDetailsLoading] = useState(false)

  async function loadDetails(english: string) {
    setDetails(null)
    // Solo para palabras/frases cortas (los sinónimos/ejemplos no aplican a párrafos)
    if (!english || english.split(/\s+/).length > 8) return
    setDetailsLoading(true)
    try { setDetails(await api.translateDetails(english)) } catch { /* noop */ } finally { setDetailsLoading(false) }
  }

  async function translate(withNote = '') {
    if (!text.trim()) { toast(t('trans.writeFirst'), 'error'); return }
    setLoading(true)
    try {
      const r = await api.translate(text, direction, withNote)
      setOutput(r.translation)
      if (withNote) setNoteOpen(false)
      const english = direction === 'EN→ES' ? text
        : direction === 'ES→EN' ? r.translation
          : (isSpanish(text) ? r.translation : text)
      loadDetails(english)
    } catch (e: any) { toast(e.message, 'error') } finally { setLoading(false) }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <Card className="flex flex-col gap-3">
        <textarea value={text} onChange={(e) => setText(e.target.value)} rows={3} placeholder={t('trans.placeholder')}
          translate="no" className="rounded-xl border border-line bg-surface px-3 py-2.5 text-sm" />
        <div className="flex flex-wrap items-center justify-between gap-2">
          <Segmented options={['Auto', 'ES→EN', 'EN→ES']} value={direction} onChange={setDirection} />
          <Button onClick={() => translate()} loading={loading}><Languages size={16} />{t('btn.translate')}</Button>
        </div>

        {output && (
          <div className="flex flex-col gap-2">
            <div className="rounded-xl bg-surface2 p-4 text-base" translate="no">{output}</div>
            <div className="flex flex-wrap gap-2">
              <TtsButton text={output} label={t('btn.listen')} />
              <Button variant="outline" onClick={() => setNoteOpen((v) => !v)}>
                <Pencil size={16} />{t('btn.dispute')}
              </Button>
            </div>

            {noteOpen && (
              <div className="flex flex-col gap-2 rounded-xl border border-line p-3">
                <p className="text-sm text-muted">{t('trans.disputeIntro')}</p>
                <input value={note} onChange={(e) => setNote(e.target.value)} placeholder={t('trans.notePlaceholder')}
                  className="rounded-lg border border-line bg-surface px-3 py-2 text-sm" />
                <div className="flex gap-2">
                  <Button onClick={() => translate(note)} loading={loading}>
                    <RefreshCw size={16} />{t('btn.translateAgain')}
                  </Button>
                  <Button variant="outline" onClick={() => { setNoteOpen(false); setNote('') }}>
                    <X size={16} />{t('btn.close')}
                  </Button>
                </div>
              </div>
            )}

            {(detailsLoading || (details && (details.synonyms.length > 0 || details.examples.length > 0))) && (
              <div className="flex flex-col gap-3 rounded-xl border border-line p-3 text-sm">
                {detailsLoading && <div className="flex items-center gap-2 text-muted"><Spinner size={14} />…</div>}
                {details && details.synonyms.length > 0 && (
                  <div>
                    <div className="mb-1 font-bold">{t('trans.synonyms')}</div>
                    <div className="flex flex-wrap gap-2" translate="no">
                      {details.synonyms.map((s) => (
                        <button key={s} onClick={() => playTTS(s, { lang: 'en' })}
                          className="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface2 px-3 py-1 font-semibold hover:border-accent">
                          <Volume2 size={13} />{s}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                {details && details.examples.length > 0 && (
                  <div>
                    <div className="mb-1 font-bold">{t('trans.examples')}</div>
                    <ul className="flex flex-col gap-1.5">
                      {details.examples.map((ex, i) => (
                        <li key={i} className="rounded-lg bg-surface2 px-3 py-2">
                          <button onClick={() => playTTS(ex.en, { lang: 'en' })}
                            className="inline-flex items-start gap-1.5 text-left font-semibold hover:text-accent" translate="no">
                            <Volume2 size={13} className="mt-1 shrink-0" />{ex.en}
                          </button>
                          {ex.es && <div className="text-muted">{ex.es}</div>}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  )
}
