import { useEffect, useRef, useState } from 'react'
import { Play, Send, RotateCcw, Volume2, X } from 'lucide-react'
import { api, type ConversationTurn } from '../api'
import { Button, Card, MicRecorder, Select, Thinking, SpeedControl, playTTS, useToast } from '../ui'
import { useI18n } from '../i18n'
import type { TabProps } from '../App'

interface Msg { role: 'user' | 'assistant'; content: string; fb?: ConversationTurn }

// Marca una burbuja del asistente que aún se está generando (muestra el estado "pensando").
const THINKING = ''
const isThinking = (c: string) => c === THINKING || c === ''

export default function Conversation({ level, scenarios, award }: TabProps) {
  const toast = useToast()
  const { t } = useI18n()
  const [scenario, setScenario] = useState('')
  const [detail, setDetail] = useState('')
  const [review, setReview] = useState(true)          // revisar el texto antes de enviarlo
  const [draft, setDraft] = useState<string | null>(null)  // transcripción pendiente de revisar
  const [messages, setMessages] = useState<Msg[]>([])
  const [loading, setLoading] = useState(false)
  const chatEnd = useRef<HTMLDivElement | null>(null)

  useEffect(() => { if (scenarios.length && !scenario) setScenario(scenarios[0]) }, [scenarios])
  useEffect(() => { chatEnd.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  function awardTurn(score?: number | null) {
    const sc = typeof score === 'number' ? score : undefined
    award(sc != null ? Math.round(sc / 10) : 1, (sc ?? 0) >= 80, { kind: 'conversation', level, score: sc })
  }

  async function start() {
    setLoading(true)
    setDraft(null)
    setMessages([{ role: 'assistant', content: THINKING }])   // burbuja "pensando"
    try {
      const { reply } = await api.conversationStart(level, scenario, detail)
      setMessages([{ role: 'assistant', content: reply }])
      playTTS(reply, { lang: 'en' })
    } catch (e: any) { setMessages([]); toast(e.message, 'error') } finally { setLoading(false) }
  }

  async function send(blob: Blob) {
    setLoading(true)
    const form = new FormData()
    form.append('level', level)
    form.append('scenario', scenario)
    form.append('detail', detail)
    form.append('history', JSON.stringify(messages))
    form.append('audio', blob, 'turn.webm')
    // Burbuja "pensando" inmediata: cubre la transcripción y la generación.
    setMessages((m) => [...m, { role: 'assistant', content: THINKING }])
    try {
      const res = await fetch('/api/conversation/turn_stream', { method: 'POST', body: form })
      if (!res.ok || !res.body) {
        let msg = `Error ${res.status}`
        try { msg = (await res.json()).detail || msg } catch { /* noop */ }
        throw new Error(msg)
      }
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buf = ''
      for (;;) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        let idx: number
        while ((idx = buf.indexOf('\n\n')) >= 0) {
          const chunk = buf.slice(0, idx); buf = buf.slice(idx + 2)
          const dataLine = chunk.split('\n').find((l) => l.startsWith('data: '))
          if (!dataLine) continue
          const ev = JSON.parse(dataLine.slice(6))
          if (ev.type === 'user') {
            // Inserta lo que dijo el usuario JUSTO antes de la burbuja "pensando".
            setMessages((m) => { const nm = [...m]; nm.splice(nm.length - 1, 0, { role: 'user', content: ev.text }); return nm })
          } else if (ev.type === 'partial') {
            setMessages((m) => { const nm = [...m]; nm[nm.length - 1] = { role: 'assistant', content: ev.reply }; return nm })
          } else if (ev.type === 'done') {
            setMessages((m) => {
              const nm = [...m]
              nm[nm.length - 1] = { role: 'assistant', content: ev.reply }
              const ui = nm.length - 2   // el mensaje del usuario de este turno
              if (ui >= 0 && nm[ui].role === 'user') {
                nm[ui] = { ...nm[ui], fb: {
                  user_text: nm[ui].content, reply: ev.reply, corrections: ev.corrections,
                  vocab_tip: ev.vocab_tip, pron_words: ev.pron_words, score: ev.score } }
              }
              return nm
            })
            playTTS(ev.reply, { lang: 'en' })
            awardTurn(ev.score)   // la IA puntúa el turno; da puntos y nutre el área 🗣️
          } else if (ev.type === 'error') {
            setMessages((m) => (m.length && m[m.length - 1].role === 'assistant' && isThinking(m[m.length - 1].content) ? m.slice(0, -1) : m))
            toast(ev.message, 'error')
          }
        }
      }
    } catch (e: any) {
      setMessages((m) => (m.length && m[m.length - 1].role === 'assistant' && isThinking(m[m.length - 1].content) ? m.slice(0, -1) : m))
      toast(e.message, 'error')
    } finally { setLoading(false) }
  }

  // Modo "Revisar": transcribe el audio (sin enviar al tutor) y muestra el texto para corregirlo.
  async function transcribeForReview(blob: Blob) {
    setLoading(true)
    try {
      const r = await api.conversationTranscribe(blob)
      setDraft(r.user_text)
    } catch (e: any) { toast(e.message, 'error') } finally { setLoading(false) }
  }

  // Envía el texto (ya revisado) al tutor.
  async function sendText(text: string) {
    if (!text.trim()) return
    setLoading(true)
    const base = messages
    setDraft(null)
    setMessages([...base, { role: 'user', content: text }, { role: 'assistant', content: THINKING }])
    try {
      const data = await api.conversationTurnText(level, scenario, base, text, detail)
      setMessages([...base, { role: 'user', content: data.user_text, fb: data }, { role: 'assistant', content: data.reply }])
      playTTS(data.reply, { lang: 'en' })
      awardTurn(data.score)
    } catch (e: any) { setMessages(base); setDraft(text); toast(e.message, 'error') } finally { setLoading(false) }
  }

  function onRecorded(blob: Blob) {
    if (review) transcribeForReview(blob)
    else send(blob)
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[3fr_2fr]">
      <Card className="flex flex-col">
        <div className="chat-scroll flex h-[460px] flex-col gap-3 overflow-y-auto pr-1">
          {messages.length === 0 && (
            <div className="m-auto max-w-xs text-center text-muted">{t('conv.empty')}</div>
          )}
          {messages.map((m, i) => (
            <div key={i} className="flex flex-col gap-1.5">
              <div className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] rounded-2xl px-3.5 py-2 text-sm ${
                  m.role === 'user' ? 'bg-accent text-accentFg' : 'bg-surface2 text-text'}`}>
                  {m.role === 'assistant' && isThinking(m.content) ? <Thinking /> : m.content}
                </div>
              </div>
              {m.role === 'user' && m.fb && <TurnFeedback fb={m.fb} />}
            </div>
          ))}
          <div ref={chatEnd} />
        </div>
        <div className="mt-3 border-t border-line pt-3">
          <MicRecorder onRecorded={onRecorded} onReset={() => setDraft(null)}
            disabled={loading} hint={t('conv.micHint')} />

          {draft !== null && (
            <div className="mt-3 rounded-xl border border-accent bg-accentSoft p-3">
              <div className="mb-1 text-xs font-bold uppercase tracking-wide text-muted">{t('conv.reviewLabel')}</div>
              <textarea value={draft} onChange={(e) => setDraft(e.target.value)} rows={2} translate="no"
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendText(draft) } }}
                className="w-full rounded-lg border border-line bg-surface px-2.5 py-1.5 text-sm" />
              <div className="mt-2 flex gap-2">
                <Button onClick={() => sendText(draft)} loading={loading}><Send size={14} />{t('btn.send')}</Button>
                <Button variant="outline" onClick={() => setDraft(null)}><X size={14} />{t('btn.cancel')}</Button>
              </div>
            </div>
          )}

          <div className="mt-3 flex flex-wrap gap-2">
            <Button variant="ghost" onClick={start} loading={loading}><Play size={16} />{t('btn.start')}</Button>
            <Button variant="outline" onClick={() => { setMessages([]); setDraft(null) }}>
              <RotateCcw size={16} />{t('conv.reset')}
            </Button>
            <SpeedControl className="ml-auto" />
          </div>
        </div>
      </Card>

      <div className="flex flex-col gap-4">
        <Card className="flex flex-col gap-3">
          <label className="text-sm font-bold text-muted">{t('conv.scenario')}</label>
          <Select value={scenario} onChange={setScenario} options={scenarios} />
          <input value={detail} onChange={(e) => setDetail(e.target.value)} placeholder={t('conv.detailPh')}
            className="rounded-xl border border-line bg-surface px-3 py-2.5 text-sm" />
          <label className="flex cursor-pointer items-center gap-2 text-sm font-semibold">
            <input type="checkbox" className="accent-[var(--accent)]" checked={review}
              onChange={(e) => setReview(e.target.checked)} />
            {t('conv.review')}
          </label>
          <p className="text-xs text-muted">{t('conv.reviewHint')}</p>
        </Card>
        <Card>
          <p className="text-sm text-muted">{t('conv.analysisInline')}</p>
        </Card>
      </div>
    </div>
  )
}

// Correcciones + nota + tip + pronunciación, en contexto bajo el mensaje del usuario.
function TurnFeedback({ fb }: { fb: ConversationTurn }) {
  const { t } = useI18n()
  const hasCorr = fb.corrections.length > 0
  if (!hasCorr && !fb.vocab_tip && !fb.pron_words.length && typeof fb.score !== 'number') return null
  return (
    <div className="flex justify-end">
      <div className="max-w-[85%] rounded-xl border border-line bg-surface2/60 px-3 py-2 text-xs">
        <div className="mb-1 flex items-center gap-2">
          <span className="font-bold uppercase tracking-wide text-muted">{t('conv.analysis')}</span>
          {typeof fb.score === 'number' && (
            <span className="ml-auto font-extrabold text-accent">{fb.score}<span className="text-muted">/100</span></span>
          )}
        </div>
        {hasCorr ? (
          <ul className="flex flex-col gap-1">
            {fb.corrections.map((c, i) => (
              <li key={i}>
                <span className="text-bad line-through" translate="no">{c.original}</span>{' → '}
                <span className="font-bold text-good" translate="no">{c.correction}</span>
                {c.explanation && <div className="text-muted">{c.explanation}</div>}
              </li>
            ))}
          </ul>
        ) : <div className="font-semibold text-good">{t('conv.noErrors')}</div>}
        {fb.vocab_tip && <div className="mt-1"><b>{t('conv.vocab')}</b> {fb.vocab_tip}</div>}
        {fb.pron_words.length > 0 && (
          <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
            <span className="text-muted">{t('conv.pronWatch')}</span>
            {fb.pron_words.map((w) => (
              <button key={w} onClick={() => playTTS(w, { lang: 'en', slow: true })} translate="no"
                className="inline-flex items-center gap-1 rounded-full border border-line bg-surface px-2 py-0.5 font-semibold hover:border-accent">
                <Volume2 size={12} />{w}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
