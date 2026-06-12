import { useEffect, useState } from 'react'
import { Plus, Sparkles, Volume2 } from 'lucide-react'
import { api, type FlashState } from '../api'
import { Button, Card, playTTS, useToast } from '../ui'
import { useI18n } from '../i18n'

export default function Flashcards() {
  const toast = useToast()
  const { t } = useI18n()
  const [state, setState] = useState<FlashState | null>(null)
  const [flipped, setFlipped] = useState(false)
  const [front, setFront] = useState('')
  const [busy, setBusy] = useState(false)

  async function load() { try { setState(await api.flashcards()) } catch (e: any) { toast(e.message, 'error') } }
  useEffect(() => { load() }, [])

  async function review(grade: string) {
    if (!state?.card) return
    setBusy(true)
    try { setState(await api.flashcardReview(state.card.id, grade)); setFlipped(false) }
    catch (e: any) { toast(e.message, 'error') } finally { setBusy(false) }
  }
  async function add() {
    if (!front.trim()) return
    setBusy(true)
    try { setState(await api.flashcardAdd(front.trim())); setFront('') }
    catch (e: any) { toast(e.message, 'error') } finally { setBusy(false) }
  }
  async function seed() {
    setBusy(true)
    try { const r = await api.flashcardSeed(); setState(r); toast(`+${r.added}`, 'success') }
    catch (e: any) { toast(e.message, 'error') } finally { setBusy(false) }
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4">
      <Card className="flex flex-col gap-4">
        <p className="rounded-lg bg-surface2 p-3 text-sm text-muted">{t('fc.help')}</p>
        <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
          <span className="text-muted">
            {t('fc.due')}: <b className="text-text">{state?.due ?? 0}</b> · {t('fc.total')}: <b className="text-text">{state?.total ?? 0}</b>
          </span>
          <Button variant="outline" onClick={seed} loading={busy}><Sparkles size={15} />{t('fc.seed')}</Button>
        </div>

        {state?.card ? (
          <div className="flex flex-col items-center gap-4 rounded-2xl border border-line bg-surface2 p-8">
            <button onClick={() => playTTS(state.card!.front, { lang: 'en' })}
              className="inline-flex items-center gap-2 text-2xl font-extrabold hover:text-accent" translate="no">
              <Volume2 size={18} />{state.card.front}
            </button>
            {flipped
              ? <div className="text-lg text-muted">{state.card.back || '—'}</div>
              : <Button variant="ghost" onClick={() => setFlipped(true)}>{t('fc.show')}</Button>}
            {flipped && (
              <div className="flex flex-wrap justify-center gap-2">
                <Button variant="outline" onClick={() => review('again')} loading={busy}>{t('fc.again')}</Button>
                <Button onClick={() => review('good')} loading={busy}>{t('fc.good')}</Button>
                <Button variant="ghost" onClick={() => review('easy')} loading={busy}>{t('fc.easy')}</Button>
              </div>
            )}
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-line p-8 text-center text-muted">{t('fc.empty')}</div>
        )}

        <div className="flex gap-2">
          <input value={front} onChange={(e) => setFront(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && add()} placeholder={t('fc.addPlaceholder')}
            translate="no" className="flex-1 rounded-xl border border-line bg-surface px-3 py-2.5 text-sm" />
          <Button onClick={add} loading={busy}><Plus size={16} />{t('fc.add')}</Button>
        </div>
      </Card>
    </div>
  )
}
