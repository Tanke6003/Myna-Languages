import { useEffect, useState, type ReactNode } from 'react'
import { MemoryStick, Cpu, Monitor, Mic, RefreshCw, Check, Download, Star, Trash2 } from 'lucide-react'
import { api, type SystemInfo } from '../api'
import { Button, Card, Segmented, Select, Spinner, useToast } from '../ui'
import { useI18n } from '../i18n'

function Row({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center gap-2 rounded-lg bg-surface2 px-3 py-2 text-sm">
      <span className="text-accent">{icon}</span>
      <span className="font-bold">{label}</span>
      <span className="ml-auto text-muted">{value}</span>
    </div>
  )
}

export default function Settings() {
  const toast = useToast()
  const { t } = useI18n()
  const [info, setInfo] = useState<SystemInfo | null>(null)
  const [model, setModel] = useState('')
  const [whisper, setWhisper] = useState('')
  const [device, setDevice] = useState('gpu')
  const [saving, setSaving] = useState(false)
  const [pulling, setPulling] = useState<string | null>(null)
  const [pullPct, setPullPct] = useState<number | null>(null)
  const [pullStatus, setPullStatus] = useState('')

  async function load() {
    try {
      const s = await api.system()
      setInfo(s); setModel(s.current_model); setWhisper(s.whisper_model); setDevice(s.llm_device)
    } catch (e: any) { toast(e.message, 'error') }
  }
  useEffect(() => { load() }, [])

  async function apply(chosen: string) {
    setSaving(true)
    try {
      const r = await api.setModel(chosen)
      setModel(r.current_model)
      setInfo((i) => (i ? { ...i, current_model: r.current_model } : i))
      toast(`${t('settings.applied')}: ${r.current_model}`, 'success')
    } catch (e: any) { toast(e.message, 'error') } finally { setSaving(false) }
  }

  async function applyDevice(chosen: string) {
    setSaving(true)
    try {
      const r = await api.setDevice(chosen)
      setDevice(r.llm_device)
      setInfo((i) => (i ? { ...i, llm_device: r.llm_device } : i))
      toast(`${t('settings.applied')}: ${r.llm_device.toUpperCase()}`, 'success')
    } catch (e: any) { toast(e.message, 'error') } finally { setSaving(false) }
  }

  async function applyWhisper(chosen: string) {
    setSaving(true)
    try {
      const r = await api.setWhisper(chosen)
      setWhisper(r.whisper_model)
      setInfo((i) => (i ? { ...i, whisper_model: r.whisper_model } : i))
      toast(`${t('settings.applied')}: ${r.whisper_model}`, 'success')
    } catch (e: any) { toast(e.message, 'error') } finally { setSaving(false) }
  }

  async function pull(name: string) {
    setPulling(name); setPullPct(null); setPullStatus('')
    try {
      const finalModel = await api.pullModel(name, (ev) => { setPullStatus(ev.status); setPullPct(ev.pct ?? null) })
      toast(`${t('settings.applied')}: ${finalModel}`, 'success')
      await load()
    } catch (e: any) { toast(e.message, 'error') } finally { setPulling(null) }
  }

  async function del(name: string) {
    if (!window.confirm(`${t('settings.deleteConfirm')}\n\n${name}`)) return
    try {
      await api.deleteModel(name)
      toast(`${t('settings.delete')}: ${name}`, 'success')
      await load()
    } catch (e: any) { toast(e.message, 'error') }
  }

  if (!info) {
    return <div className="mx-auto max-w-2xl"><Card><p className="text-sm text-muted">…</p></Card></div>
  }

  const gpuValue = info.gpu.nvidia ? (info.gpu.name || `NVIDIA ×${info.gpu.count}`) : t('settings.none')
  const installed = info.available_models.length ? info.available_models : [info.current_model]

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4">
      <Card className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h3 className="font-extrabold">{t('settings.system')}</h3>
          <Button variant="outline" onClick={load}><RefreshCw size={15} />{t('settings.refresh')}</Button>
        </div>
        <div className="grid gap-2 sm:grid-cols-2">
          <div className="flex items-center gap-2 rounded-lg bg-surface2 px-3 py-2 text-sm sm:col-span-2">
            <span className="text-accent"><Cpu size={16} /></span>
            <span className="font-bold">CPU</span>
            <span className="ml-auto truncate text-muted" title={info.cpu_name}>
              {info.cpu_name ? `${info.cpu_name} · ` : ''}{info.cpu_cores}c/{info.cpu_threads}t
              {info.cpu_ghz ? ` @ ${info.cpu_ghz} GHz` : ''}
            </span>
          </div>
          <Row icon={<MemoryStick size={16} />} label="RAM" value={`${info.ram_gb} GB`} />
          <Row icon={<Monitor size={16} />} label={t('settings.gpu')} value={gpuValue} />
          {info.vram_gb > 0 && <Row icon={<Monitor size={16} />} label={t('settings.vram')} value={`${info.vram_gb} GB`} />}
          <Row icon={<Mic size={16} />} label={t('settings.whisper')} value={info.whisper_device.toUpperCase()} />
        </div>
      </Card>

      {/* Modelo de IA: cambio rápido entre instalados */}
      <Card className="flex flex-col gap-3">
        <h3 className="font-extrabold">{t('settings.model')}</h3>
        <p className="text-sm text-muted">{t('settings.noRestart')}</p>
        <div className="flex flex-wrap items-center gap-2">
          <Select value={model} onChange={setModel} options={installed} className="min-w-44" />
          <Button onClick={() => apply(model)} loading={saving}><Check size={16} />{t('settings.apply')}</Button>
        </div>
        <div className="flex flex-wrap items-center gap-2 border-t border-line pt-3">
          <span className="text-sm font-bold">{t('settings.device')}</span>
          <Segmented options={['GPU', 'CPU']} value={device.toUpperCase()}
            onChange={(v) => applyDevice(v.toLowerCase())} />
          <span className="text-xs text-muted">
            {info.gpu_available ? t('settings.deviceHint') : t('settings.noGpu')}
          </span>
        </div>
      </Card>

      {/* Catálogo según tus recursos (con descarga) */}
      <Card className="flex flex-col gap-3">
        <h3 className="font-extrabold">{t('settings.catalog')}</h3>
        <p className="text-sm text-muted">{t('settings.catalogHint').replace('{budget}', String(info.budget_gb))}</p>
        <div className="flex flex-col gap-2">
          {info.model_catalog.map((m) => (
            <div key={m.name}
              className={`flex flex-wrap items-center gap-2 rounded-xl border p-2.5 ${
                m.name === info.recommended_model ? 'border-accent bg-accentSoft' : 'border-line'} ${
                !m.fits ? 'opacity-50' : ''}`}>
              <span className="font-bold" translate="no">{m.name}</span>
              <span className="text-xs text-muted">{m.label} · ~{m.gb} GB</span>
              {m.name === info.recommended_model && (
                <span className="inline-flex items-center gap-1 rounded-full bg-accent px-2 py-0.5 text-xs font-bold text-accentFg">
                  <Star size={11} />{t('settings.recommendedBadge')}
                </span>
              )}
              <div className="ml-auto flex items-center gap-2">
                {m.installed ? (
                  m.name === info.current_model ? (
                    <span className="text-xs font-bold text-good">{t('settings.active')}</span>
                  ) : (
                    <>
                      {m.fits && <Button variant="outline" onClick={() => apply(m.name)} loading={saving}>{t('settings.use')}</Button>}
                      <button onClick={() => del(m.name)} title={t('settings.delete')}
                        className="flex h-9 w-9 items-center justify-center rounded-xl border border-line text-muted hover:border-bad hover:text-bad">
                        <Trash2 size={15} />
                      </button>
                    </>
                  )
                ) : m.fits ? (
                  pulling === m.name
                    ? <span className="inline-flex items-center gap-2 text-xs text-muted">
                        <Spinner size={12} />{pullStatus}{pullPct != null ? ` ${pullPct}%` : ''}
                      </span>
                    : <Button variant="outline" onClick={() => pull(m.name)} disabled={!!pulling}>
                        <Download size={15} />{t('settings.install')}
                      </Button>
                ) : (
                  <span className="text-xs font-semibold text-bad">{t('settings.notFit')}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Whisper */}
      <Card className="flex flex-col gap-3">
        <h3 className="font-extrabold">{t('settings.whisperModel')}</h3>
        <p className="text-sm text-muted">{t('settings.whisperHint')}</p>
        <div className="flex flex-wrap items-center gap-2">
          <Select value={whisper} onChange={setWhisper} options={info.whisper_sizes} className="min-w-44" />
          <Button onClick={() => applyWhisper(whisper)} loading={saving}><Check size={16} />{t('settings.apply')}</Button>
        </div>
      </Card>
    </div>
  )
}
