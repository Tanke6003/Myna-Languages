import { useEffect, useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'
import { api } from '../api'
import { useI18n } from '../i18n'
import { Spinner } from './primitives'

/* Pista del significado (traducción al español) oculta tras un "ojito" */
export function HintToggle({ text }: { text: string }) {
  const { t } = useI18n()
  const [open, setOpen] = useState(false)
  const [hint, setHint] = useState('')
  const [loading, setLoading] = useState(false)
  useEffect(() => { setOpen(false); setHint('') }, [text])
  async function toggle() {
    if (!open && !hint) {
      setLoading(true)
      try { setHint((await api.translate(text, 'EN→ES')).translation) } catch { /* noop */ }
      setLoading(false)
    }
    setOpen((o) => !o)
  }
  return (
    <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted">
      <button onClick={toggle} className="inline-flex items-center gap-1 font-semibold hover:text-text">
        {open ? <EyeOff size={13} /> : <Eye size={13} />}{t('hint.show')}
      </button>
      {loading && <Spinner size={12} />}
      {open && hint && <span>{hint}</span>}
    </div>
  )
}
