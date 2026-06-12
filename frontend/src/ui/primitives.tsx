import { type ButtonHTMLAttributes, type ReactNode } from 'react'
import { Loader2 } from 'lucide-react'

export function Spinner({ size = 16 }: { size?: number }) {
  return <Loader2 size={size} className="animate-spin" />
}

export type BtnVariant = 'primary' | 'ghost' | 'outline'

export function Button(
  { children, variant = 'primary', loading, className = '', ...props }:
  { children: ReactNode; variant?: BtnVariant; loading?: boolean } &
  ButtonHTMLAttributes<HTMLButtonElement>,
) {
  const base = 'inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold transition disabled:opacity-50 disabled:cursor-not-allowed'
  const variants: Record<BtnVariant, string> = {
    primary: 'bg-accent text-accentFg hover:brightness-110 shadow-soft',
    ghost: 'bg-surface2 text-text hover:brightness-95',
    outline: 'border border-line text-text hover:bg-surface2',
  }
  return (
    <button className={`${base} ${variants[variant]} ${className}`}
      disabled={loading || props.disabled} {...props}>
      {loading ? <Spinner /> : null}{children}
    </button>
  )
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-2xl border border-line bg-surface p-4 shadow-soft ${className}`}>{children}</div>
}

export function Pill({ children }: { children: ReactNode }) {
  return <span className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border border-line bg-surface2 px-3 py-1 text-sm font-bold">{children}</span>
}

export function Segmented(
  { options, value, onChange }:
  { options: string[]; value: string; onChange: (v: string) => void },
) {
  return (
    <div className="inline-flex flex-wrap gap-1 rounded-xl bg-surface2 p-1">
      {options.map((o) => (
        <button key={o} onClick={() => onChange(o)}
          className={`rounded-lg px-3 py-1.5 text-sm font-bold transition ${
            value === o ? 'bg-surface text-accent shadow-soft' : 'text-muted hover:text-text'}`}>
          {o}
        </button>
      ))}
    </div>
  )
}

export function Select(
  { value, onChange, options, className = '' }:
  { value: string; onChange: (v: string) => void; options: string[]; className?: string },
) {
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)}
      className={`rounded-xl border border-line bg-surface px-3 py-2.5 text-sm font-bold text-text ${className}`}>
      {options.map((o) => <option key={o} value={o}>{o}</option>)}
    </select>
  )
}
