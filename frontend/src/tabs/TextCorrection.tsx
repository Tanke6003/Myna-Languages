import { useState } from 'react'
import { Sparkles, CheckCircle2, XCircle } from 'lucide-react'
import { api, type TextCheck } from '../api'
import { Button, Card, useToast } from '../ui'
import { useI18n } from '../i18n'
import type { TabProps } from '../App'

export default function TextCorrection({ level, award }: TabProps) {
  const toast = useToast()
  const { t } = useI18n()
  const [sentence, setSentence] = useState('')
  const [fix, setFix] = useState('')
  const [result, setResult] = useState<TextCheck | null>(null)
  const [loadingNew, setLoadingNew] = useState(false)
  const [loadingCheck, setLoadingCheck] = useState(false)

  async function newSentence() {
    setLoadingNew(true)
    try {
      const r = await api.textNew(level)
      setSentence(r.sentence); setFix(''); setResult(null)
    } catch (e: any) { toast(e.message, 'error') } finally { setLoadingNew(false) }
  }

  async function check() {
    if (!sentence) { toast(t('text.genFirst'), 'error'); return }
    if (!fix.trim()) { toast(t('text.writeFirst'), 'error'); return }
    setLoadingCheck(true)
    try {
      const r = await api.textCheck(sentence, fix)
      setResult(r)
      await award(r.correct ? 10 : 0, r.correct, { kind: 'text', level })
    } catch (e: any) { toast(e.message, 'error') } finally { setLoadingCheck(false) }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <Card className="flex flex-col gap-3">
        <Button onClick={newSentence} loading={loadingNew}><Sparkles size={16} />{t('btn.newErrors')}</Button>
        {sentence
          ? <div className="rounded-xl bg-surface2 p-4 text-lg font-bold" translate="no">{sentence}</div>
          : <p className="text-sm text-muted">{t('text.startHint')}</p>}
        <textarea value={fix} onChange={(e) => setFix(e.target.value)} rows={2} placeholder={t('text.placeholder')}
          translate="no" className="rounded-xl border border-line bg-surface px-3 py-2.5 text-sm" />
        <Button onClick={check} loading={loadingCheck} disabled={!sentence}>
          <CheckCircle2 size={16} />{t('btn.check')}
        </Button>
        {result && (
          <div className="rounded-xl border border-line p-3 text-sm">
            <div className={`flex items-center gap-1.5 font-extrabold ${result.correct ? 'text-good' : 'text-bad'}`}>
              {result.correct ? <CheckCircle2 size={18} /> : <XCircle size={18} />}
              {result.correct ? t('text.correct') : t('text.almost')}
            </div>
            {result.fixed && <p className="mt-1" translate="no"><b>{t('text.correctSentence')}</b> {result.fixed}</p>}
            {result.feedback && <p className="mt-1 text-muted">{result.feedback}</p>}
          </div>
        )}
      </Card>
    </div>
  )
}
