import { useEffect, useState } from 'react'
import { Home, GraduationCap, Sun, Moon, ArrowUp, Sparkles } from 'lucide-react'
import { api, type AwardMeta, type LevelUp, type Meta, type Stats, type Medals } from './api'

const MEDAL_ORDER = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
import { Button, Scoreboard, Segmented, useTheme, useToast } from './ui'
import { useI18n } from './i18n'
import { MODULES, CATEGORIES, moduleById } from './modules'
import Onboarding from './Onboarding'
import HomeView from './tabs/Home'
import Conversation from './tabs/Conversation'
import Reading from './tabs/Reading'
import Shadowing from './tabs/Shadowing'
import Dictation from './tabs/Dictation'
import Listening from './tabs/Listening'
import TextCorrection from './tabs/TextCorrection'
import Vocabulary from './tabs/Vocabulary'
import Flashcards from './tabs/Flashcards'
import Mixed from './tabs/Mixed'
import Translator from './tabs/Translator'
import Progress from './tabs/Progress'
import Settings from './tabs/Settings'

export interface TabProps {
  level: string
  scenarios: string[]
  award: (points: number, correct: boolean, meta?: AwardMeta) => Promise<void>
}

export default function App() {
  const { dark, toggle } = useTheme()
  const { t, lang, setLang } = useI18n()
  const toast = useToast()
  const [meta, setMeta] = useState<Meta | null>(null)
  const [level, setLevel] = useState('B1')
  const [stats, setStats] = useState<Stats | null>(null)
  const [tab, setTab] = useState('home')
  const [progressKey, setProgressKey] = useState(0)
  const [levelup, setLevelup] = useState<LevelUp | null>(null)
  const [celebrate, setCelebrate] = useState<string | null>(null)
  const [onboard, setOnboard] = useState(() => !localStorage.getItem('onboarded'))

  useEffect(() => {
    api.meta().then((m) => { setMeta(m); setLevel(m.default_level) }).catch((e) => toast(e.message, 'error'))
    api.stats().then(setStats).catch(() => {})
  }, [])

  useEffect(() => {
    if (level) api.levelup(level).then(setLevelup).catch(() => {})
  }, [level, progressKey])

  // Medallas: si la medalla más alta sube respecto a la última vista, celebra con animación.
  useEffect(() => {
    api.medals().then((m: Medals) => {
      const stored = localStorage.getItem('myna.medalHighest')
      if (stored === null) {            // primera vez: inicializa sin celebrar lo ya conseguido
        localStorage.setItem('myna.medalHighest', m.highest ?? '')
        return
      }
      const newIdx = m.highest ? MEDAL_ORDER.indexOf(m.highest) : -1
      const oldIdx = stored ? MEDAL_ORDER.indexOf(stored) : -1
      if (newIdx > oldIdx) {
        localStorage.setItem('myna.medalHighest', m.highest ?? '')
        setCelebrate(m.highest)
      }
    }).catch(() => {})
  }, [progressKey])

  const award = async (points: number, correct: boolean, meta?: AwardMeta) => {
    try {
      setStats(await api.award(points, correct, meta))
      setProgressKey((k) => k + 1)
    } catch { /* noop */ }
  }

  const ctx: TabProps = { level, scenarios: meta?.scenarios ?? [], award }

  function NavItem({ id, Icon }: { id: string; Icon: typeof Home }) {
    const activeItem = tab === id
    return (
      <button onClick={() => setTab(id)}
        className={`flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm font-semibold transition ${
          activeItem ? 'bg-accentSoft text-accent' : 'text-muted hover:bg-surface2 hover:text-text'}`}>
        <Icon size={17} />{t('nav.' + id)}
      </button>
    )
  }

  const activeMod = moduleById(tab)

  return (
    <div className="flex min-h-screen">
      {/* Sidebar (escritorio) */}
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col gap-1 overflow-y-auto border-r border-line bg-surface p-3 md:flex">
        <button onClick={() => setTab('home')} className="mb-2 flex items-center gap-2 px-1 py-1 text-left">
          <img src="/myna_app_tile.svg" alt="Myna" className="h-9 w-9 rounded-xl" />
          <b className="text-base font-extrabold">{t('app.title')}</b>
        </button>
        <NavItem id="home" Icon={Home} />
        {CATEGORIES.map((cat) => (
          <div key={cat} className="mt-2">
            <div className="px-2 pb-1 text-[11px] font-bold uppercase tracking-wide text-muted">{t('cat.' + cat)}</div>
            {MODULES.filter((m) => m.cat === cat).map((m) => <NavItem key={m.id} id={m.id} Icon={m.Icon} />)}
          </div>
        ))}
      </aside>

      {/* Columna principal */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-4 py-3">
          {/* Navegación compacta en móvil */}
          <select value={tab} onChange={(e) => setTab(e.target.value)}
            className="rounded-xl border border-line bg-surface px-3 py-2 text-sm font-bold md:hidden">
            <option value="home">{t('nav.home')}</option>
            {MODULES.map((m) => <option key={m.id} value={m.id}>{t('nav.' + m.id)}</option>)}
          </select>
          <div className="hidden md:block" />
          <div className="flex flex-wrap items-center gap-3">
            {meta && <Segmented options={meta.levels} value={level} onChange={setLevel} />}
            <Scoreboard stats={stats} />
            <button onClick={() => setLang(lang === 'es' ? 'en' : 'es')} title={t('lang.title')}
              className="flex h-10 w-10 items-center justify-center rounded-xl border border-line bg-surface text-sm font-extrabold hover:bg-surface2">
              {lang === 'es' ? 'EN' : 'ES'}
            </button>
            <button onClick={toggle} title={t('theme.title')}
              className="flex h-10 w-10 items-center justify-center rounded-xl border border-line bg-surface hover:bg-surface2">
              {dark ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </div>
        </header>

        <main className="p-4 md:p-6">
          {/* Sugerencia de subir de nivel */}
          {levelup?.ready && levelup.next_level && (
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-accent bg-accentSoft p-3">
              <span className="flex items-center gap-2 font-semibold">
                <GraduationCap size={18} className="text-accent" /> {t('levelup.msg')} {levelup.next_level}?
              </span>
              <Button onClick={() => { setLevel(levelup.next_level!); setLevelup(null) }}>
                <ArrowUp size={16} />{t('levelup.up')} {levelup.next_level}
              </Button>
            </div>
          )}

          {/* Cabecera del módulo activo */}
          {tab !== 'home' && activeMod && (
            <div className="mb-4 flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-accentSoft text-accent">
                <activeMod.Icon size={20} />
              </span>
              <div>
                <h2 className="text-lg font-extrabold leading-tight">{t('nav.' + tab)}</h2>
                <p className="text-sm text-muted">{t('mod.' + tab + '.desc')}</p>
              </div>
            </div>
          )}

          <div className={tab === 'home' ? '' : 'hidden'}>
            <HomeView onOpen={setTab} level={level} refreshKey={progressKey}
              onLevelUp={() => { if (levelup?.next_level) { setLevel(levelup.next_level); setLevelup(null) } }} />
          </div>
          <div className={tab === 'conv' ? '' : 'hidden'}><Conversation {...ctx} /></div>
          <div className={tab === 'read' ? '' : 'hidden'}><Reading {...ctx} /></div>
          <div className={tab === 'shadowing' ? '' : 'hidden'}><Shadowing {...ctx} /></div>
          <div className={tab === 'dictation' ? '' : 'hidden'}><Dictation {...ctx} /></div>
          <div className={tab === 'listening' ? '' : 'hidden'}><Listening {...ctx} /></div>
          <div className={tab === 'text' ? '' : 'hidden'}><TextCorrection {...ctx} /></div>
          <div className={tab === 'vocab' ? '' : 'hidden'}><Vocabulary {...ctx} /></div>
          <div className={tab === 'flashcards' ? '' : 'hidden'}><Flashcards /></div>
          <div className={tab === 'mixed' ? '' : 'hidden'}><Mixed {...ctx} active={tab === 'mixed'} /></div>
          <div className={tab === 'trans' ? '' : 'hidden'}><Translator {...ctx} /></div>
          <div className={tab === 'progress' ? '' : 'hidden'}><Progress refreshKey={progressKey} /></div>
          <div className={tab === 'settings' ? '' : 'hidden'}><Settings /></div>
        </main>
      </div>

      {onboard && (
        <Onboarding onDone={() => { localStorage.setItem('onboarded', '1'); setOnboard(false) }} />
      )}

      {/* Celebración al conseguir una medalla (dominar un nivel) */}
      {celebrate && (
        <div onClick={() => setCelebrate(null)}
          className="animate-overlay-in fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div onClick={(e) => e.stopPropagation()}
            className="flex flex-col items-center gap-4 rounded-3xl border border-line bg-surface p-8 text-center shadow-soft">
            <div className="text-xs font-bold uppercase tracking-wide text-accent">{t('medal.unlocked')}</div>
            <img src={`/medals/medal_${celebrate}.svg`} alt={celebrate} className="animate-medal h-40 w-40" />
            <div className="text-2xl font-extrabold">{t('medal.levelReached').replace('{level}', celebrate)} 🎉</div>
            <Button onClick={() => setCelebrate(null)}><Sparkles size={16} />{t('medal.cta')}</Button>
          </div>
        </div>
      )}
    </div>
  )
}
