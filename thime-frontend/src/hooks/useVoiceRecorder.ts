import { useState, useRef, useCallback } from 'react'

type RecorderState = 'idle' | 'recording' | 'stopped'

export function useVoiceRecorder() {
  const [state, setState] = useState<RecorderState>('idle')
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [durationSec, setDurationSec] = useState(0)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<BlobPart[]>([])
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const start = useCallback(async () => {
    chunksRef.current = []
    setAudioBlob(null)
    setAudioUrl(null)
    setDurationSec(0)

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4'
    const recorder = new MediaRecorder(stream, { mimeType })

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data)
    }

    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: mimeType })
      const url = URL.createObjectURL(blob)
      setAudioBlob(blob)
      setAudioUrl(url)
      stream.getTracks().forEach((t) => t.stop())
    }

    recorder.start(250)
    mediaRecorderRef.current = recorder
    setState('recording')

    timerRef.current = setInterval(() => setDurationSec((s) => s + 1), 1000)
  }, [])

  const stop = useCallback(() => {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop()
    }
    if (timerRef.current) clearInterval(timerRef.current)
    setState('stopped')
  }, [])

  const reset = useCallback(() => {
    if (audioUrl) URL.revokeObjectURL(audioUrl)
    setAudioBlob(null)
    setAudioUrl(null)
    setDurationSec(0)
    setState('idle')
  }, [audioUrl])

  const fileExt = audioBlob?.type.includes('webm') ? 'webm' : 'mp4'

  return { state, audioBlob, audioUrl, durationSec, fileExt, start, stop, reset }
}
