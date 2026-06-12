import { useEffect, useRef, useState } from 'react'
import { Play, Send, RotateCcw, Volume2, Pencil, X } from 'lucide-react'
import { api, type ConversationTurn } from '../api'
import { Button, Card, MicRecorder, Select, Thinking, SpeedControl, playTTS, useToast } from '../ui'
import { useI18n } from '../i18n'
import type { TabProps } from '../App'

interface Msg { role: 'user' | 'assistant'; content: string }

// Marca una burbuja del asistente que aún se está generando (muestra el estado "pensando").
const THINKING = ''
const isThinking = (c: string) => c === THINKING || c === ''

export default function Conversation({ level, scenarios }: TabProps) {
  const toast = useToast()
  const { t } = useI18n()
  const [scenario, setScenario] = useState('')
  const [detail, setDetail] = useState('')
  const [autoSend, setAutoSend] = useState(true)
  const [messages, setMessages] = useState<Msg[]>([])
  const [fb, setFb] = useState<ConversationTurn | null>(null)
  const [loading, setLoading] = useState(false)
  const lastBlob = useRef<Blob | null>(null)
  const chatEnd = useRef<HTMLDivElement | null>(null)

  useEffect(() => { if (scenarios.length && !scenario) setScenario(scenarios[0]) }, [scenarios])
  useEffect(() => { chatEnd.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  async function start() {
    setLoading(true)
    setFb(null)
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
    let userText = ''
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
            userText = ev.text
            // Inserta lo que dijo el usuario JUSTO antes de la burbuja "pensando".
            setMessages((m) => { const nm = [...m]; nm.splice(nm.length - 1, 0, { role: 'user', content: ev.text }); return nm })
          } else if (ev.type === 'partial') {
            setMessages((m) => { const nm = [...m]; nm[nm.length - 1] = { role: 'assistant', content: ev.reply }; return nm })
          } else if (ev.type === 'done') {
            setMessages((m) => { const nm = [...m]; nm[nm.length - 1] = { role: 'assistant', content: ev.reply }; return nm })
            setFb({ user_text: userText, reply: ev.reply, corrections: ev.corrections, vocab_tip: ev.vocab_tip, pron_words: ev.pron_words })
            playTTS(ev.reply, { lang: 'en' })
          } else if (ev.type === 'error') {
            setMessages((m) => (m.length && m[m.length - 1].role === 'assistant' && isThinking(m[m.length - 1].content) ? m.slice(0, -1) : m))
            toast(ev.message, 'error')
          }
        }
      }
    } catch (e: any) {
      // Quita la burbuja "pensando" si quedó colgada por un error.
      setMessages((m) => (m.length && m[m.length - 1].role === 'assistant' && isThinking(m[m.length - 1].content) ? m.slice(0, -1) : m))
      toast(e.message, 'error')
    } finally { setLoading(false) }
  }

  async function resend(correctedText: string) {
    setLoading(true)
    const snapshot = messages
    const base = messages.slice(0, -2)
    setMessages([...base, { role: 'user', content: correctedText }, { role: 'assistant', content: THINKING }])
    try {
      const data = await api.conversationTurnText(level, scenario, base, correctedText, detail)
      setMessages([...base, { role: 'user', content: data.user_text }, { role: 'assistant', content: data.reply }])
      setFb(data)
      playTTS(data.reply, { lang: 'en' })
    } catch (e: any) { setMessages(snapshot); toast(e.message, 'error') } finally { setLoading(false) }
  }

  function onRecorded(blob: Blob) {
    lastBlob.current = blob
    if (autoSend) send(blob)
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[3fr_2fr]">
      <Card className="flex flex-col">
        <div className="chat-scroll flex h-[460px] flex-col gap-3 overflow-y-auto pr-1">
          {messages.length === 0 && (
            <div className="m-auto max-w-xs text-center text-muted">{t('conv.empty')}</div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] rounded-2xl px-3.5 py-2 text-sm ${
                m.role === 'user' ? 'bg-accent text-accentFg' : 'bg-surface2 text-text'}`}>
                {m.role === 'assistant' && isThinking(m.content) ? <Thinking /> : m.content}
              </div>
            </div>
          ))}
          <div ref={chatEnd} />
        </div>
        <div className="mt-3 border-t border-line pt-3">
          <MicRecorder onRecorded={onRecorded} onReset={() => { lastBlob.current = null }}
            disabled={loading} hint={t('conv.micHint')} />
          <div className="mt-3 flex flex-wrap gap-2">
            <Button variant="ghost" onClick={start} loading={loading}><Play size={16} />{t('btn.start')}</Button>
            <Button onClick={() => (lastBlob.current ? send(lastBlob.current) : toast(t('conv.recordFirst'), 'error'))}
              loading={loading} disabled={autoSend}><Send size={16} />{t('btn.send')}</Button>
            <Button variant="outline" onClick={() => { setMessages([]); setFb(null) }}>
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
            <input type="checkbox" className="accent-[var(--accent)]" checked={autoSend}
              onChange={(e) => setAutoSend(e.target.checked)} />
            {t('conv.handsfree')}
          </label>
        </Card>
        <Card>
          <h3 className="mb-2 font-extrabold">{t('conv.analysis')}</h3>
          {!fb && <p className="text-sm text-muted">{t('conv.analysisEmpty')}</p>}
          {fb && <ConvFeedback fb={fb} onResend={resend} loading={loading} />}
        </Card>
      </div>
    </div>
  )
}

function ConvFeedback(
  { fb, onResend, loading }:
  { fb: ConversationTurn; onResend: (t: string) => void; loading: boolean },
) {
  const { t } = useI18n()
  const [editing, setEditing] = useState(false)
  const [text, setText] = useState(fb.user_text)
  useEffect(() => { setText(fb.user_text); setEditing(false) }, [fb])

  return (
    <div className="flex flex-col gap-3 text-sm">
      <div className="rounded-lg bg-surface2 p-2.5">
        <div className="mb-1 flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wide text-muted">{t('conv.heard')}</span>
          {!editing && (
            <button onClick={() => setEditing(true)}
              className="inline-flex items-center gap-1 text-xs font-bold text-accent hover:underline">
              <Pencil size={13} />{t('btn.edit')}
            </button>
          )}
        </div>
        {!editing ? (
          <i>{fb.user_text}</i>
        ) : (
          <div className="flex flex-col gap-2">
            <textarea value={text} onChange={(e) => setText(e.target.value)} rows={2}
              className="w-full rounded-lg border border-line bg-surface px-2.5 py-1.5 text-sm" />
            <div className="flex gap-2">
              <Button onClick={() => onResend(text)} loading={loading}><Send size={14} />{t('btn.resend')}</Button>
              <Button variant="outline" onClick={() => { setEditing(false); setText(fb.user_text) }}>
                <X size={14} />{t('btn.cancel')}
              </Button>
            </div>
          </div>
        )}
      </div>

      {fb.corrections.length > 0 ? (
        <div>
          <div className="mb-1 font-bold">{t('conv.corrections')}</div>
          <ul className="flex flex-col gap-1.5">
            {fb.corrections.map((c, i) => (
              <li key={i} className="rounded-lg bg-surface2 px-3 py-2">
                <span className="text-bad line-through">{c.original}</span>{' → '}
                <span className="font-bold text-good">{c.correction}</span>
                {c.explanation && <div className="text-muted">{c.explanation}</div>}
              </li>
            ))}
          </ul>
        </div>
      ) : <p className="text-good">{t('conv.noErrors')}</p>}

      {fb.vocab_tip && <p><b>{t('conv.vocab')}</b> {fb.vocab_tip}</p>}

      {fb.pron_words.length > 0 && (
        <div>
          <div className="mb-1 font-bold">{t('conv.pronWatch')}</div>
          <div className="flex flex-wrap gap-2">
            {fb.pron_words.map((w) => (
              <button key={w} onClick={() => playTTS(w, { lang: 'en', slow: true })}
                className="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface2 px-3 py-1 text-sm font-semibold hover:border-accent">
                <Volume2 size={14} />{w}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
