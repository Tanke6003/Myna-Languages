import { createContext, useCallback, useContext, useState, type ReactNode } from 'react'
import { Info, AlertTriangle, CheckCircle2 } from 'lucide-react'

type ToastType = 'info' | 'error' | 'success'
interface Toast { id: number; message: string; type: ToastType }

const ToastCtx = createContext<(m: string, t?: ToastType) => void>(() => {})
export const useToast = () => useContext(ToastCtx)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const push = useCallback((message: string, type: ToastType = 'info') => {
    const id = Date.now() + Math.random()
    setToasts((t) => [...t, { id, message, type }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4500)
  }, [])
  const styles: Record<ToastType, { cls: string; Icon: typeof Info }> = {
    info: { cls: 'border-line', Icon: Info },
    error: { cls: 'border-bad', Icon: AlertTriangle },
    success: { cls: 'border-good', Icon: CheckCircle2 },
  }
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex w-80 flex-col gap-2">
        {toasts.map((t) => {
          const { cls, Icon } = styles[t.type]
          return (
            <div key={t.id}
              className={`flex items-start gap-2 rounded-xl border bg-surface px-3 py-2.5 text-sm shadow-soft ${cls}`}>
              <Icon size={18} className="mt-0.5 shrink-0 text-muted" />
              <span className="text-text">{t.message}</span>
            </div>
          )
        })}
      </div>
    </ToastCtx.Provider>
  )
}
