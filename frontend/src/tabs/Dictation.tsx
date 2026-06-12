import { useState } from 'react'
import { Headphones, Volume2, CheckCircle2 } from 'lucide-react'
import { api } from '../api'
import { Button, Card, playTTS, useToast } from '../ui'
import { useI18n } from '../i18n'
import type { TabProps } from '../App'

function norm(s: string) {
  return s.toLowerCase().replace(/[^\w\s']/g, ' ').split(/\s+/).filter(Boolean)
}
function lcs(a: string[], b: string[]) {
  const m = a.length, n = b.length
  const d = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0))
  for (let i = 1; i <= m; i++)
    for (let j = 1; j <= n; j++)
      d[i][j] = a[i - 1] === b[j - 1] ? d[i - 1][j - 1] + 1 : Math.max(d[i - 1][j], d[i][j - 1])
  return d[m][n]
}

export default function Dictation({ level, award }: TabProps) {
  const toast = useToast()
  const { t } = useI18n()
  const [sentence, setSentence] = useState('')
  const [typed, setTyped] = useState('')
  const [result, setResult] = useState<{ score: number; missed: string[] } | null>(null)
  const [loading, setLoading] = useState(false)

  async function newDictation() {
    setLoading(true)
    try {
      const r = await api.readingSentence(level, '')
      setSentence(r.sentence); setTyped(''); setResult(null)
      playTTS(r.sentence, { lang: 'en' })
    } catch (e: any) { toast(e.message, 'error') } finally { setLoading(false) }
  }

  function check() {
    if (!sentence) { toast(t('dict.first'), 'error'); return }
    if (!typed.trim()) { toast(t('dict.writeFirst'), 'error'); return }
    const ref = norm(sentence), hyp = norm(typed)
    const score = Math.round(100 * lcs(ref, hyp) / Math.max(ref.length, 1))
    const missed = ref.filter((w) => !hyp.includes(w))
    setResult({ score, missed })
    award(Math.round(score / 10), score >= 80, { kind: 'dictation', level, score, words: missed })
  }

  return (
    <div className="mx-auto max-w-2xl">
      <Card className="flex flex-col gap-3">
        <p className="text-sm text-muted">{t('dict.intro')}</p>
        <div className="flex flex-wrap gap-2">
          <Button onClick={newDictation} loading={loading}><Headphones size={16} />{t('btn.newDictation')}</Button>
          {sentence && (
            <>
              <Button variant="outline" onClick={() => playTTS(sentence, { lang: 'en' })}>
                <Volume2 size={16} />{t('btn.repeat')}
              </Button>
              <Button variant="outline" onClick={() => playTTS(sentence, { lang: 'en', slow: true })}>
                <Volume2 size={16} />{t('btn.slow')}
              </Button>
            </>
          )}
        </div>
        <textarea value={typed} onChange={(e) => setTyped(e.target.value)} rows={2}
          placeholder={t('dict.placeholder')}
          className="rounded-xl border border-line bg-surface px-3 py-2.5 text-sm" />
        <Button onClick={check} disabled={!sentence}><CheckCircle2 size={16} />{t('btn.check')}</Button>
        {result && (
          <div className="rounded-xl border border-line p-3 text-sm">
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-extrabold text-accent">{result.score}</span>
              <span className="text-muted">/ 100</span>
            </div>
            <p className="mt-1" translate="no"><b>{t('dict.correctSentence')}</b> {sentence}</p>
            {result.missed.length > 0 && (
              <p className="mt-1 text-muted" translate="no">{t('dict.missed')} {result.missed.join(', ')}</p>
            )}
          </div>
        )}
      </Card>
    </div>
  )
}
