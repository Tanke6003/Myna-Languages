import { useState } from 'react'
import { Sparkles, CheckCircle2, Volume2 } from 'lucide-react'
import { api, type ReadingReport } from '../api'
import { Button, Card, HintToggle, MicRecorder, Thinking, TtsButton, SpeedControl, ReportRepeat, playTTS, useToast } from '../ui'
import { useI18n } from '../i18n'
import type { TabProps } from '../App'

export default function Reading({ level, award }: TabProps) {
  const toast = useToast()
  const { t } = useI18n()
  const [topic, setTopic] = useState('')
  const [sentence, setSentence] = useState('')
  const [ipa, setIpa] = useState('')
  const [blob, setBlob] = useState<Blob | null>(null)
  const [report, setReport] = useState<ReadingReport | null>(null)
  const [loadingNew, setLoadingNew] = useState(false)
  const [loadingEval, setLoadingEval] = useState(false)

  async function newSentence() {
    setLoadingNew(true)
    try {
      const r = await api.readingSentence(level, topic)
      setSentence(r.sentence); setIpa(r.ipa); setReport(null); setBlob(null)
    } catch (e: any) { toast(e.message, 'error') } finally { setLoadingNew(false) }
  }

  async function evaluate() {
    if (!blob) { toast(t('read.recordFirst'), 'error'); return }
    setLoadingEval(true)
    try {
      const rep = await api.readingEvaluate(level, sentence, blob)
      setReport(rep)
      await award(Math.round(rep.score / 10), rep.score >= 80, {
        kind: 'reading', level, score: rep.score, words: rep.problems.map((p) => p.word),
      })
    } catch (e: any) { toast(e.message, 'error') } finally { setLoadingEval(false) }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[3fr_2fr]">
      <Card className="flex flex-col gap-3">
        <div className="flex gap-2">
          <input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder={t('read.topic')}
            className="flex-1 rounded-xl border border-line bg-surface px-3 py-2.5 text-sm" />
          <Button onClick={newSentence} loading={loadingNew}><Sparkles size={16} />{t('btn.newSentence')}</Button>
        </div>
        {loadingNew ? (
          <div className="rounded-xl bg-surface2 p-4"><Thinking /></div>
        ) : sentence ? (
          <div className="rounded-xl bg-surface2 p-4">
            <div className="text-lg font-bold" translate="no">{sentence}</div>
            <div className="mt-1 text-sm text-muted">{ipa}</div>
            <HintToggle text={sentence} />
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <TtsButton text={sentence} lang="en" slow label={t('btn.hearModel')} />
              <SpeedControl />
              <ReportRepeat onReport={newSentence} loading={loadingNew} className="ml-auto" />
            </div>
          </div>
        ) : <p className="text-sm text-muted">{t('read.startHint')}</p>}
        <MicRecorder onRecorded={setBlob} hint={t('read.micHint')} />
        <Button onClick={evaluate} loading={loadingEval} disabled={!sentence}>
          <CheckCircle2 size={16} />{t('btn.evaluate')}
        </Button>
      </Card>

      <Card>
        {!report && <p className="text-sm text-muted">{t('read.evalEmpty')}</p>}
        {report && <ReadingResult report={report} />}
      </Card>
    </div>
  )
}

function ReadingResult({ report }: { report: ReadingReport }) {
  const { t } = useI18n()
  return (
    <div className="flex flex-col gap-3 text-sm">
      <div className="flex items-baseline gap-2">
        <span className="text-3xl font-extrabold text-accent">{report.score}</span>
        <span className="text-muted">/ 100</span>
      </div>
      <p className="leading-relaxed" translate="no">
        {report.words.map((w, i) => (
          <span key={i} className={
            w.status === 'ok' ? '' : w.status === 'wrong' ? 'font-bold text-bad underline decoration-wavy'
              : 'font-bold text-accent'}>
            {w.word}{' '}
          </span>
        ))}
      </p>
      <div className="text-muted">{t('read.heardLabel')} “{report.heard}”</div>
      <TtsButton text={report.reference} lang="en" slow label={t('btn.correctPron')} />
      {report.problems.length > 0 && (
        <div>
          <div className="mb-1 font-bold">{t('read.wordsToPractice')}</div>
          <div className="flex flex-col gap-1.5">
            {report.problems.map((p, i) => (
              <div key={i} className="rounded-lg bg-surface2 px-3 py-1.5">
                <div className="flex items-center justify-between">
                  <span translate="no"><b>{p.word}</b> {p.phonemes && <span className="text-muted">{p.phonemes.ipa}</span>}</span>
                  <button onClick={() => playTTS(p.word, { lang: 'en', slow: true })} className="text-accent hover:brightness-110">
                    <Volume2 size={16} />
                  </button>
                </div>
                {p.sound_diff && p.sound_diff.subs.length > 0 && (
                  <div className="mt-1 text-xs" translate="no">
                    <span className="text-muted">{t('read.soundedLike')} {p.sound_diff.heard_ipa}</span>
                    <div className="mt-1 flex flex-wrap items-center gap-1">
                      <span className="text-muted">{t('read.fixSounds')}</span>
                      {p.sound_diff.subs.map((s, k) => (
                        <span key={k} className="rounded bg-bad/10 px-1.5 py-0.5 font-mono text-bad">
                          {s.expected}<span className="text-muted">→</span>{s.heard}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
      {report.feedback && <div className="rounded-lg border border-line p-3">{report.feedback}</div>}
    </div>
  )
}
