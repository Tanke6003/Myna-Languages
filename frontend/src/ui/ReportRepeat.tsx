import { RotateCcw } from 'lucide-react'
import { useI18n } from '../i18n'

/** Botón discreto «este ejercicio ya lo hice / repetido»: pide otro distinto.
 * El backend ya recuerda los ejercicios servidos, así que al pedir otro evita el actual. */
export function ReportRepeat({ onReport, loading, className = '' }:
  { onReport: () => void; loading?: boolean; className?: string }) {
  const { t } = useI18n()
  return (
    <button type="button" onClick={onReport} disabled={loading} title={t('repeat.hint')}
      className={`inline-flex items-center gap-1.5 text-xs font-bold text-muted transition hover:text-accent disabled:opacity-50 ${className}`}>
      <RotateCcw size={14} />{t('repeat.btn')}
    </button>
  )
}
