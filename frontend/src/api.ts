// Cliente de la API + tipos (contrato con el backend FastAPI).

export interface Meta { levels: string[]; default_level: string; scenarios: string[] }
export interface Stats { points: number; streak: number; best: number; level: number }

export interface Correction { original: string; correction: string; explanation: string }
export interface ConversationTurn {
  user_text: string
  reply: string
  corrections: Correction[]
  vocab_tip: string
  pron_words: string[]
}

export interface Phonemes { arpabet: string; ipa: string }
export interface SoundStep { status: 'ok' | 'sub' | 'missing' | 'extra'; expected: string; heard: string }
export interface SoundSub { expected: string; heard: string }
export interface SoundDiff { score: number; heard_ipa: string; steps: SoundStep[]; subs: SoundSub[] }
export interface WordStatus { word: string; status: 'ok' | 'wrong' | 'missing'; heard?: string }
export interface ProblemWord extends WordStatus { phonemes?: Phonemes | null; sound_diff?: SoundDiff | null }
export interface ReadingReport {
  score: number
  reference: string
  heard: string
  words: WordStatus[]
  problems: ProblemWord[]
  feedback: string
}

export interface TextCheck { correct: boolean; fixed: string; feedback: string }

export interface ActivityTotal { kind: string; count: number; avg_score: number | null }
export interface ActivityItem {
  ts: string; kind: string; level: string | null; score: number | null; correct: number | null
}
export interface MissedWord { word: string; count: number }
export interface Progress {
  stats: Stats
  totals: ActivityTotal[]
  recent: ActivityItem[]
  missed: MissedWord[]
  total_count: number
}
export interface AwardMeta { kind?: string; level?: string; score?: number; words?: string[] }

export interface SystemInfo {
  ram_gb: number
  cpu_cores: number
  cpu_threads: number
  gpu: { nvidia: boolean; count: number; name: string }
  vram_gb: number
  budget_gb: number
  whisper_device: string
  whisper_model: string
  whisper_sizes: string[]
  current_model: string
  available_models: string[]
  recommended_model: string
  model_catalog: CatalogModel[]
}
export interface CatalogModel {
  name: string
  gb: number
  label: string
  family: string
  fits: boolean
  installed: boolean
}
export interface VocabExercise {
  prompt: string
  question: string
  options: string[]
  answer: string
  explain: string
}

export interface ListeningExercise {
  passage: string
  question: string
  options: string[]
  answer: string
  explain: string
}

export interface TranslationDetails {
  word: string
  synonyms: string[]
  examples: { en: string; es: string }[]
}

export interface Flashcard { id: number; front: string; back: string }
export interface FlashState { total: number; due: number; card: Flashcard | null; added?: number }

export interface MixedItem {
  empty: boolean
  word?: string
  type?: 'meaning' | 'listen'
  options?: string[]
  answer?: string
  explain?: string
  remaining?: number
}
export interface LevelUp {
  level: string
  next_level: string | null
  ready: boolean
  need: number
  count: number
  avg_score: number | null
}
export interface HomeData {
  missed: { word: string; count: number }[]
  missed_count: number
  total_activity: number
  flashcards_due: number
  flashcards_total: number
  levelup: LevelUp
}

async function handle(res: Response) {
  if (!res.ok) {
    let detail = `Error ${res.status}`
    try { detail = (await res.json()).detail || detail } catch { /* noop */ }
    throw new Error(detail)
  }
  return res.json()
}

function postJSON(path: string, body: unknown) {
  return fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(handle)
}

function postForm(path: string, form: FormData) {
  return fetch(path, { method: 'POST', body: form }).then(handle)
}

export const api = {
  meta: (): Promise<Meta> => fetch('/api/meta').then(handle),
  stats: (): Promise<Stats> => fetch('/api/stats').then(handle),
  award: (points: number, correct: boolean, meta: AwardMeta = {}): Promise<Stats> =>
    postJSON('/api/stats/award', { points, correct, ...meta }),
  resetStats: (): Promise<Stats> => fetch('/api/stats/reset', { method: 'POST' }).then(handle),
  progress: (): Promise<Progress> => fetch('/api/progress').then(handle),
  exportProgress: (): Promise<unknown> => fetch('/api/progress/export').then(handle),
  importProgress: (data: unknown): Promise<Progress> => postJSON('/api/progress/import', data),

  system: (): Promise<SystemInfo> => fetch('/api/system').then(handle),
  setModel: (model: string): Promise<{ current_model: string }> =>
    postJSON('/api/settings/model', { model }),
  setWhisper: (model: string): Promise<{ whisper_model: string }> =>
    postJSON('/api/settings/whisper', { model }),
  deleteModel: (model: string): Promise<{ ok: boolean }> =>
    postJSON('/api/settings/delete', { model }),
  pullModel: async (
    model: string, onEvent: (ev: { status: string; pct?: number | null }) => void,
  ): Promise<string> => {
    const form = new FormData(); form.append('model', model)
    const res = await fetch('/api/settings/pull', { method: 'POST', body: form })
    if (!res.ok || !res.body) throw new Error('No se pudo iniciar la descarga')
    const reader = res.body.getReader()
    const dec = new TextDecoder()
    let buf = ''
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buf += dec.decode(value, { stream: true })
      let idx: number
      while ((idx = buf.indexOf('\n\n')) >= 0) {
        const chunk = buf.slice(0, idx); buf = buf.slice(idx + 2)
        const line = chunk.split('\n').find((l) => l.startsWith('data: '))
        if (!line) continue
        const ev = JSON.parse(line.slice(6))
        if (ev.status === 'error') throw new Error(ev.message || 'Error')
        if (ev.status === 'done') return ev.model as string
        onEvent(ev)
      }
    }
    throw new Error('La descarga terminó inesperadamente')
  },

  flashcards: (): Promise<FlashState> => fetch('/api/flashcards').then(handle),
  flashcardAdd: (front: string): Promise<FlashState> => postJSON('/api/flashcards/add', { front }),
  flashcardReview: (id: number, grade: string): Promise<FlashState> =>
    postJSON('/api/flashcards/review', { id, grade }),
  flashcardSeed: (): Promise<FlashState> =>
    fetch('/api/flashcards/seed', { method: 'POST' }).then(handle),

  mixedNext: (): Promise<MixedItem> => fetch('/api/mixed/next').then(handle),
  mixedResult: (word: string, correct: boolean): Promise<{ ok: boolean }> =>
    postJSON('/api/mixed/result', { word, correct }),
  levelup: (level: string): Promise<LevelUp> =>
    fetch(`/api/levelup?level=${encodeURIComponent(level)}`).then(handle),
  home: (level: string): Promise<HomeData> =>
    fetch(`/api/home?level=${encodeURIComponent(level)}`).then(handle),

  conversationStart: (level: string, scenario: string, detail = ''): Promise<{ reply: string }> => {
    const f = new FormData()
    f.append('level', level); f.append('scenario', scenario); f.append('detail', detail)
    return postForm('/api/conversation/start', f)
  },
  conversationTurn: (
    level: string, scenario: string, history: unknown, audio: Blob,
  ): Promise<ConversationTurn> => {
    const f = new FormData()
    f.append('level', level)
    f.append('scenario', scenario)
    f.append('history', JSON.stringify(history))
    f.append('audio', audio, 'turn.webm')
    return postForm('/api/conversation/turn', f)
  },
  conversationTurnText: (
    level: string, scenario: string, history: unknown, user_text: string, detail = '',
  ): Promise<ConversationTurn> =>
    postJSON('/api/conversation/turn_text', { level, scenario, detail, history, user_text }),

  readingSentence: (level: string, topic: string): Promise<{ sentence: string; ipa: string }> =>
    postJSON('/api/reading/sentence', { level, topic }),
  readingEvaluate: (level: string, sentence: string, audio: Blob): Promise<ReadingReport> => {
    const f = new FormData()
    f.append('level', level)
    f.append('sentence', sentence)
    f.append('audio', audio, 'reading.webm')
    return postForm('/api/reading/evaluate', f)
  },

  textNew: (level: string): Promise<{ sentence: string }> => postJSON('/api/text/new', { level }),
  textCheck: (original: string, correction: string): Promise<TextCheck> =>
    postJSON('/api/text/check', { original, correction }),

  vocabNew: (level: string, kind: string): Promise<VocabExercise> =>
    postJSON('/api/vocab/new', { level, kind }),
  listeningNew: (level: string): Promise<ListeningExercise> =>
    postJSON('/api/listening/new', { level }),

  translate: (text: string, direction: string, note = ''): Promise<{ translation: string }> =>
    postJSON('/api/translate', { text, direction, note }),
  translateDetails: (text: string): Promise<TranslationDetails> =>
    postJSON('/api/translate/details', { text }),
}

// URL para reproducir audio TTS (cacheado en el backend).
export function ttsUrl(text: string, opts: { lang?: string; slow?: boolean } = {}) {
  const p = new URLSearchParams({ text })
  if (opts.lang) p.set('lang', opts.lang)
  if (opts.slow) p.set('slow', 'true')
  return `/api/tts?${p.toString()}`
}
