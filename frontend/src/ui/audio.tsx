import { useEffect, useRef, useState } from 'react'
import { Volume2, Play, Pause } from 'lucide-react'
import { ttsUrl } from '../api'
import { Button, type BtnVariant } from './primitives'

export function playTTS(text: string, opts: { lang?: string; slow?: boolean } = {}) {
  const audio = new Audio(ttsUrl(text, opts))
  audio.play().catch(() => {})
  return audio
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

/* Reproductor propio (play/pausa + barra), a juego con el tema */
export function AudioPlayer({ src, label }: { src: string; label?: string }) {
  const ref = useRef<HTMLAudioElement | null>(null)
  const [playing, setPlaying] = useState(false)
  const [progress, setProgress] = useState(0)
  useEffect(() => { setPlaying(false); setProgress(0) }, [src])
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
      <audio ref={ref} src={src} className="hidden"
        onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)} onEnded={() => setPlaying(false)}
        onTimeUpdate={(e) => { const a = e.currentTarget; setProgress(a.duration ? 100 * a.currentTime / a.duration : 0) }} />
    </div>
  )
}
