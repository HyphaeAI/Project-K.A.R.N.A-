import { useState, useRef } from 'react'

export function useMediaRecorder(stream, onChunk) {
  const [isRecording, setIsRecording] = useState(false)
  const recorderRef = useRef(null)
  const finalCallbackRef = useRef(null)
  const chunksRef = useRef([])

  const startRecording = () => {
    if (!stream || isRecording) return

    const mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp8,opus')
      ? 'video/webm;codecs=vp8,opus'
      : 'video/webm'

    const recorder = new MediaRecorder(stream, { mimeType })
    recorderRef.current = recorder
    chunksRef.current = []

    recorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        // If we have a final callback queued, this is the last chunk
        if (finalCallbackRef.current) {
          finalCallbackRef.current(event.data, true)
          finalCallbackRef.current = null
        } else {
          onChunk(event.data, false)
        }
      }
    }

    recorder.start(5000)
    setIsRecording(true)
  }

  const stopRecording = (onFinalChunk) => {
    if (!recorderRef.current || !isRecording) return
    finalCallbackRef.current = onFinalChunk
    recorderRef.current.stop()
    setIsRecording(false)
  }

  return { startRecording, stopRecording, isRecording }
}
