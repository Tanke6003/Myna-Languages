import { useRef, useState } from 'react'
import { Mic, Square, RotateCcw } from 'lucide-react'
import { useI18n } from '../i18n'
import { useToast } from './toast'
import { AudioPlayer } from './audio'

export function MicRecorder(
  { onRecorded, onReset, disabled, hint }:
  { onRecorded: (b: Blob) => void; onReset?: () => void; disabled?: boolean; hint?: string },
) {
  const [recording, setRecording] = useState(false)
  const [url, setUrl] = useState<string | null>(null)
  const mrRef = useRef<MediaRecorder | null>(null)
  const chunks = useRef<Blob[]>([])
  const toast = useToast()
  const { t } = useI18n()

  function reset() {
    setUrl((u) => { if (u) URL.revokeObjectURL(u); return null })
    onReset?.()
  }

  async function start() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      })
      const mr = new MediaRecorder(stream)
      chunks.current = []
      mr.ondataavailable = (e) => { if (e.data.size) chunks.current.push(e.data) }
      mr.onstop = () => {
        const blob = new Blob(chunks.current, { type: 'audio/webm' })
        setUrl((u) => { if (u) URL.revokeObjectURL(u); return URL.createObjectURL(blob) })
        stream.getTracks().forEach((tr) => tr.stop())
        onRecorded(blob)
      }
      mr.start()
      mrRef.current = mr
      setRecording(true)
    } catch {
      toast(t('mic.permission'), 'error')
    }
  }
  function stop() { mrRef.current?.stop(); setRecording(false) }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-3">
        <button onClick={recording ? stop : start} disabled={disabled}
          className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-full text-white transition disabled:opacity-40 ${
            recording ? 'bg-bad recording-pulse' : 'bg-accent hover:brightness-110'}`}>
          {recording ? <Square size={18} fill="currentColor" /> : <Mic size={20} />}
        </button>
        <div className="text-sm text-muted">
          {recording ? t('mic.recording') : (hint || t('mic.idle'))}
        </div>
      </div>
      {url && !recording && (
        <div className="flex items-center gap-2">
          <div className="flex-1"><AudioPlayer src={url} label={t('mic.yourRecording')} /></div>
          <button onClick={reset} title={t('mic.reset')} aria-label={t('mic.reset')}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-line bg-surface text-muted hover:border-bad hover:text-bad">
            <RotateCcw size={16} />
          </button>
        </div>
      )}
    </div>
  )
}
