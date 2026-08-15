import { useRef, useState } from 'react'

// Die Web Speech API ist nicht Teil der Standard-TS-DOM-Typen (experimentell,
// nur in Chrome/Edge zuverlaessig verfuegbar) - minimaler eigener Typ statt `any`.
type SpeechRecognitionResultLike = {
  isFinal: boolean
  0: { transcript: string }
}

type SpeechRecognitionEventLike = {
  resultIndex: number
  results: ArrayLike<SpeechRecognitionResultLike>
}

type SpeechRecognitionLike = {
  lang: string
  continuous: boolean
  interimResults: boolean
  start: () => void
  stop: () => void
  onresult: ((event: SpeechRecognitionEventLike) => void) | null
  onerror: (() => void) | null
  onend: (() => void) | null
}

function getSpeechRecognitionCtor(): (new () => SpeechRecognitionLike) | null {
  const w = window as unknown as {
    SpeechRecognition?: new () => SpeechRecognitionLike
    webkitSpeechRecognition?: new () => SpeechRecognitionLike
  }
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null
}

/**
 * Diktierfunktion auf Basis der browsereigenen Spracherkennung (Web Speech
 * API) - bewusst ohne serverseitige Transkription/neue Abhaengigkeit. Die
 * Audioverarbeitung laeuft dabei im Browser bzw. beim Browser-Anbieter (z. B.
 * Googles Spracherkennungsdienst in Chrome), NICHT ueber Project-A's eigenen
 * Server - siehe Transparenzhinweis in der aufrufenden Komponente.
 */
export function useSpeechDictation(onFinalTranscript: (text: string) => void) {
  const [dictating, setDictating] = useState(false)
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null)
  const supported = getSpeechRecognitionCtor() !== null

  const toggle = () => {
    if (dictating) {
      recognitionRef.current?.stop()
      setDictating(false)
      return
    }

    const Ctor = getSpeechRecognitionCtor()
    if (!Ctor) return

    const recognition = new Ctor()
    recognition.lang = 'de-DE'
    recognition.continuous = true
    recognition.interimResults = false
    recognition.onresult = (event) => {
      let transcript = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i]
        if (result.isFinal) transcript += result[0].transcript
      }
      if (transcript.trim()) onFinalTranscript(transcript.trim())
    }
    recognition.onerror = () => setDictating(false)
    recognition.onend = () => setDictating(false)

    recognitionRef.current = recognition
    recognition.start()
    setDictating(true)
  }

  return { supported, dictating, toggle }
}
