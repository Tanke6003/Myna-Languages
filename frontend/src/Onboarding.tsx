import { GraduationCap } from 'lucide-react'
import { Button } from './ui'
import { useI18n } from './i18n'

export default function Onboarding({ onDone }: { onDone: () => void }) {
  const { t } = useI18n()
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-2xl border border-line bg-surface p-6 shadow-soft">
        <div className="mb-4 flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-accent text-accentFg">
            <GraduationCap size={24} />
          </span>
          <h2 className="text-xl font-extrabold">{t('onb.title')}</h2>
        </div>
        <ul className="flex flex-col gap-2.5 text-sm">
          <li>{t('onb.p1')}</li>
          <li>{t('onb.p2')}</li>
          <li>{t('onb.p3')}</li>
        </ul>
        <Button className="mt-5 w-full" onClick={onDone}>{t('onb.cta')}</Button>
      </div>
    </div>
  )
}
