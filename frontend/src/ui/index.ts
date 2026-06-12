// Kit de UI — re-exporta todo para que `import { X } from '../ui'` siga funcionando.
export { ToastProvider, useToast } from './toast'
export { useTheme } from './theme'
export { Spinner, Button, Card, Pill, Segmented, Select, type BtnVariant } from './primitives'
export { Scoreboard } from './Scoreboard'
export { playTTS, TtsButton, AudioPlayer, SpeedControl, getAudioSpeed, setAudioSpeed, useAudioSpeed, SPEEDS } from './audio'
export { HintToggle } from './HintToggle'
export { MicRecorder } from './MicRecorder'
export { Thinking } from './Thinking'
