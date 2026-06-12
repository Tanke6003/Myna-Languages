import { useEffect, useState } from 'react'
import { Spinner } from './primitives'
import { useI18n } from '../i18n'

// Frases rotativas mientras el modelo "piensa": hacen que la espera se sienta más corta.
const KEYS = ['think.0', 'think.1', 'think.2', 'think.3', 'think.4', 'think.5']

export function Thinking({ className = '' }: { className?: string }) {
  const { t } = useI18n()
  const [i, setI] = useState(() => Math.floor(Math.random() * KEYS.length))
  useEffect(() => {
    const id = setInterval(() => setI((x) => (x + 1) % KEYS.length), 1900)
    return () => clearInterval(id)
  }, [])
  return (
    <span className={`inline-flex items-center gap-2 text-muted ${className}`}>
      <Spinner size={14} />
      <span key={i} className="thinking-fade">{t(KEYS[i])}</span>
    </span>
  )
}
