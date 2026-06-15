import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import es from './locales/es.json'
import en from './locales/en.json'

// Los textos de cada idioma viven en src/locales/<lang>.json (para no inflar este archivo).
// Para añadir/editar un texto, edita esos JSON; aquí solo está la lógica de i18n.
export type Lang = 'es' | 'en'

const STRINGS: Record<Lang, Record<string, string>> = { es, en }

interface I18n { lang: Lang; setLang: (l: Lang) => void; t: (k: string) => string }
const Ctx = createContext<I18n>({ lang: 'es', setLang: () => {}, t: (k) => k })
export const useI18n = () => useContext(Ctx)

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(() => (localStorage.getItem('lang') as Lang) || 'es')
  useEffect(() => { localStorage.setItem('lang', lang) }, [lang])
  const t = (k: string) => STRINGS[lang][k] ?? STRINGS.es[k] ?? k
  return <Ctx.Provider value={{ lang, setLang, t }}>{children}</Ctx.Provider>
}
