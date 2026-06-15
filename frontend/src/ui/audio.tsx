import { useEffect, useRef, useState } from 'react'
import { Volume2, Play, Pause } from 'lucide-react'
import { ttsUrl } from '../api'
import { Button, type BtnVariant } from './primitives'

/* --- Velocidad de reproducción global (aplica a TODO el audio) --- */
export const SPEEDS = [0.5, 1, 1.5, 2]
const SPEED_KEY = 'myna.audioSpeed'
let _speed = 1
try {
  const s = Number(localStorage.getItem(SPEED_KEY))
  if (SPEEDS.includes(s)) _speed = s
} catch { /* noop */ }

const listeners = new Set<(s: number) => void>()
export function getAudioSpeed() { return _speed }
export function setAudioSpeed(s: number) {
  _speed = s
  try { localStorage.setItem(SPEED_KEY, String(s)) } catch { /* noop */ }
  listeners.forEach((fn) => fn(s))
}
/** Hook reactivo: re-renderiza cuando cambia la velocidad global. */
export function useAudioSpeed() {
  const [s, setS] = useState(_speed)
  useEffect(() => { listeners.add(setS); return () => { listeners.delete(setS) } }, [])
  return s
}

export function playTTS(text: string, opts: { lang?: string; slow?: boolean; voice?: string } = {}) {
  const audio = new Audio(ttsUrl(text, opts))
  audio.defaultPlaybackRate = _speed
  audio.playbackRate = _speed
  audio.addEventListener('loadedmetadata', () => { audio.playbackRate = _speed })
  audio.play().catch(() => {})
  return audio
}

/** Selector de velocidad 0.5× / 1× / 1.5× / 2× — edita la velocidad global. */
export function SpeedControl({ className = '' }: { className?: string }) {
  const s = useAudioSpeed()
  return (
    <div className={`inline-flex items-center gap-1 rounded-xl bg-surface2 p-0.5 ${className}`} title="Velocidad del audio">
      <Volume2 size={14} className="ml-1 mr-0.5 text-muted" />
      {SPEEDS.map((v) => (
        <button key={v} type="button" onClick={() => setAudioSpeed(v)}
          className={`rounded-lg px-2 py-1 text-xs font-bold transition ${
            s === v ? 'bg-accent text-accentFg' : 'text-muted hover:text-text'}`}>
          {v % 1 === 0 ? v : v.toString()}×
        </button>
      ))}
    </div>
  )
}

export function TtsButton(
  { text, lang, slow, label = 'Escuchar', variant = 'outline' as BtnVariant }:
  { text: string; lang?: string; slow?: boolean; label?: string; variant?: BtnVariant },
) {
  return (
    <Button variant={variant} onClick={() => playTTS(text, { lang, slow })}>
      <Volume2 size={16} />{label}
    </Button>
  )
}

/* Reproductor propio (play/pausa + barra + velocidad), a juego con el tema */
export function AudioPlayer({ src, label }: { src: string; label?: string }) {
  const ref = useRef<HTMLAudioElement | null>(null)
  const [playing, setPlaying] = useState(false)
  const [progress, setProgress] = useState(0)
  const speed = useAudioSpeed()
  useEffect(() => { setPlaying(false); setProgress(0) }, [src])
  useEffect(() => { if (ref.current) ref.current.playbackRate = speed }, [speed, src])
  function toggle() {
    const a = ref.current
    if (!a) return
    if (playing) a.pause(); else a.play()
  }
  return (
    <div className="flex items-center gap-3 rounded-xl border border-line bg-surface2 px-3 py-2">
      <button type="button" onClick={toggle}
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-accent text-accentFg hover:brightness-110">
        {playing ? <Pause size={16} /> : <Play size={16} className="ml-0.5" />}
      </button>
      <div className="flex-1">
        {label && <div className="mb-1 text-xs text-muted">{label}</div>}
        <div className="h-1.5 overflow-hidden rounded-full bg-line">
          <div className="h-full bg-accent" style={{ width: `${progress}%` }} />
        </div>
      </div>
      <SpeedControl />
      <audio ref={ref} src={src} className="hidden"
        onPlay={() => { if (ref.current) ref.current.playbackRate = speed; setPlaying(true) }}
        onPause={() => setPlaying(false)} onEnded={() => setPlaying(false)}
        onTimeUpdate={(e) => { const a = e.currentTarget; setProgress(a.duration ? 100 * a.currentTime / a.duration : 0) }} />
    </div>
  )
}
