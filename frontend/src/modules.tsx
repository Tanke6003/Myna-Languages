import {
  MessageCircle, Volume2, Repeat2, Headphones, Ear, SpellCheck, Brain, Layers, Shuffle,
  Languages, BarChart3, SlidersHorizontal, Lightbulb, AudioLines, PenLine,
} from 'lucide-react'

export type Category = 'speak' | 'listen' | 'write' | 'vocab' | 'tools'

export interface ModuleDef {
  id: string
  cat: Category
  Icon: typeof MessageCircle
  needsCtx?: boolean   // recibe level/award/scenarios (TabProps)
}

export const MODULES: ModuleDef[] = [
  { id: 'conv', cat: 'speak', Icon: MessageCircle, needsCtx: true },
  { id: 'read', cat: 'speak', Icon: Volume2, needsCtx: true },
  { id: 'shadowing', cat: 'speak', Icon: Repeat2, needsCtx: true },
  { id: 'dictation', cat: 'listen', Icon: Headphones, needsCtx: true },
  { id: 'listening', cat: 'listen', Icon: Ear, needsCtx: true },
  { id: 'minimal', cat: 'listen', Icon: AudioLines, needsCtx: true },
  { id: 'text', cat: 'write', Icon: SpellCheck, needsCtx: true },
  { id: 'writing', cat: 'write', Icon: PenLine, needsCtx: true },
  { id: 'vocab', cat: 'vocab', Icon: Brain, needsCtx: true },
  { id: 'concepts', cat: 'vocab', Icon: Lightbulb, needsCtx: true },
  { id: 'flashcards', cat: 'vocab', Icon: Layers },
  { id: 'mixed', cat: 'vocab', Icon: Shuffle },
  { id: 'trans', cat: 'tools', Icon: Languages, needsCtx: true },
  { id: 'progress', cat: 'tools', Icon: BarChart3 },
  { id: 'settings', cat: 'tools', Icon: SlidersHorizontal },
]

export const CATEGORIES: Category[] = ['speak', 'listen', 'write', 'vocab', 'tools']

export const moduleById = (id: string) => MODULES.find((m) => m.id === id)
