import { useState } from 'react'
import { Repeat2, Volume2, CheckCircle2, Eye } from 'lucide-react'
import { api, type ReadingReport } from '../api'
import { Button, Card, MicRecorder, Thinking, playTTS, useToast } from '../ui'
import { useI18n } from '../i18n'
import type { TabProps } from '../App'

export default function Shadowing({ level, award }: TabProps) {
  const toast = useToast()
  const { t } = useI18n()
  const [sentence, setSentence] = useState('')
  const [showText, setShowText] = useState(false)
  const [blob, setBlob] = useState<Blob | null>(null)
  const [report, setReport] = useState<ReadingReport | null>(null)
  const [loadingNew, setLoadingNew] = useState(false)
  const [loadingEval, setLoadingEval] = useState(false)

  async function newSentence() {
    setLoadingNew(true)
    try {
      const r = await api.readingSentence(level, '')
      setSentence(r.sentence); setShowText(false); setReport(null); setBlob(null)
      playTTS(r.sentence, { lang: 'en' })
    } catch (e: any) { toast(e.message, 'error') } finally { setLoadingNew(false) }
  }

  async function evaluate() {
    if (!blob) { toast(t('read.recordFirst'), 'error'); return }
    setLoadingEval(true)
    try {
      const rep = await api.readingEvaluate(level, sentence, blob)
      setReport(rep); setShowText(true)
      await award(Math.round(rep.score / 10), rep.score >= 80, {
        kind: 'shadowing', level, score: rep.score, words: rep.problems.map((p) => p.word),
      })
    } catch (e: any) { toast(e.message, 'error') } finally { setLoadingEval(false) }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <Card className="flex flex-col gap-3">
        <p className="text-sm text-muted">{t('sh.intro')}</p>
        <div className="flex flex-wrap gap-2">
          <Button onClick={newSentence} loading={loadingNew}><Repeat2 size={16} />{t('btn.newSentence')}</Button>
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
        {loadingNew && <div className="rounded-xl bg-surface2 p-3"><Thinking /></div>}
        {sentence && !showText && (
          <button onClick={() => setShowText(true)}
            className="inline-flex items-center gap-1 self-start text-xs font-semibold text-muted hover:text-text">
            <Eye size={13} />{t('sh.showText')}
          </button>
        )}
        {sentence && showText && (
          <div className="rounded-xl bg-surface2 p-4 text-lg font-bold" translate="no">{sentence}</div>
        )}
        {sentence && <MicRecorder onRecorded={setBlob} hint={t('sh.intro')} />}
        <Button onClick={evaluate} loading={loadingEval} disabled={!sentence}>
          <CheckCircle2 size={16} />{t('btn.evaluate')}
        </Button>
        {report && (
          <div className="rounded-xl border border-line p-3 text-sm">
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-extrabold text-accent">{report.score}</span>
              <span className="text-muted">/ 100</span>
            </div>
            <p className="mt-1 text-muted">{t('read.heardLabel')} “{report.heard}”</p>
            {report.problems.length > 0 && (
              <p className="mt-1" translate="no">{report.problems.map((p) => p.word).join(', ')}</p>
            )}
          </div>
        )}
      </Card>
    </div>
  )
}
