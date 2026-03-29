import { useReducer, useCallback } from 'react'
import { uploadChunk, postInit, getResults } from '../utils/chunkUploader'

const initialState = {
  sessionId: null,
  jobRole: '',
  status: 'idle',
  currentRound: 0,
  totalRounds: 5,
  currentQuestion: null,
  mediaStream: null,
  mediaRecorder: null,
  chunkQueue: [],
  chunkIndex: 0,
  roundHistory: [],
  terminalLogs: [],
  finalResults: null,
  error: null,
}

function reducer(state, action) {
  switch (action.type) {
    case 'SET_STATUS':
      return { ...state, status: action.payload }
    case 'SET_ERROR':
      return { ...state, error: action.payload }
    case 'INIT_SUCCESS':
      return {
        ...state,
        sessionId: action.payload.sessionId,
        jobRole: action.payload.jobRole,
        currentRound: action.payload.currentRound,
        totalRounds: action.payload.totalRounds,
        currentQuestion: action.payload.currentQuestion,
        status: 'recording',
        error: null,
      }
    case 'ADD_LOG':
      return {
        ...state,
        terminalLogs: [
          ...state.terminalLogs,
          {
            timestamp: new Date().toLocaleTimeString(),
            message: action.payload.message,
            type: action.payload.logType,
          },
        ],
      }
    case 'INCREMENT_CHUNK_INDEX':
      return { ...state, chunkIndex: state.chunkIndex + 1 }
    case 'UPDATE_QUESTION':
      return {
        ...state,
        currentQuestion: action.payload.question,
        currentRound: action.payload.currentRound,
      }
    case 'ADD_ROUND':
      return {
        ...state,
        roundHistory: [...state.roundHistory, action.payload],
      }
    case 'SET_FINAL_RESULTS':
      return { ...state, finalResults: action.payload }
    case 'SET_MEDIA_STREAM':
      return { ...state, mediaStream: action.payload }
    case 'SET_MEDIA_RECORDER':
      return { ...state, mediaRecorder: action.payload }
    default:
      return state
  }
}

export function useInterviewState() {
  const [state, dispatch] = useReducer(reducer, initialState)

  const addLog = useCallback((message, type = 'info') => {
    dispatch({ type: 'ADD_LOG', payload: { message, logType: type } })
  }, [])

  const fetchResults = useCallback(async (sessionId) => {
    try {
      const data = await getResults(sessionId)
      dispatch({ type: 'SET_FINAL_RESULTS', payload: data })
    } catch (err) {
      addLog(`Failed to fetch results: ${err.message}`, 'error')
    }
  }, [addLog])

  const initSession = useCallback(async (jobRole) => {
    dispatch({ type: 'SET_STATUS', payload: 'initializing' })
    addLog(`Initializing session for role: ${jobRole}`, 'info')

    try {
      const data = await postInit(jobRole)
      dispatch({
        type: 'INIT_SUCCESS',
        payload: {
          sessionId: data.session_id,
          jobRole,
          currentRound: data.current_round,
          totalRounds: data.total_rounds,
          currentQuestion: data.question,
        },
      })
      addLog(`Session created: ${data.session_id}`, 'success')
      addLog(`Round ${data.current_round}/${data.total_rounds} — ${data.question.topic_area}`, 'info')
    } catch (err) {
      dispatch({ type: 'SET_ERROR', payload: err.message })
      dispatch({ type: 'SET_STATUS', payload: 'idle' })
      addLog(`Initialization failed: ${err.message}`, 'error')
    }
  }, [addLog])

  const sendChunk = useCallback(async (blob, isFinal) => {
    const { sessionId, chunkIndex } = state

    addLog(`Sending chunk #${chunkIndex}${isFinal ? ' (final)' : ''}`, 'info')

    try {
      const data = await uploadChunk(sessionId, chunkIndex, blob, isFinal)
      dispatch({ type: 'INCREMENT_CHUNK_INDEX' })

      if (data.operations) {
        data.operations.forEach((op) => {
          addLog(`✓ ${op.op}${op.gcs_path ? ` → ${op.gcs_path}` : ''}`, 'success')
        })
      }

      if (isFinal && data.next_action) {
        const { next_action, evaluation } = data

        if (evaluation) {
          dispatch({ type: 'ADD_ROUND', payload: { ...data, round: state.currentRound } })
          if (evaluation.flags?.memorization_detected) {
            addLog('⚠ Memorization detected', 'warning')
          }
        }

        if (next_action.type === 'complete') {
          dispatch({ type: 'SET_STATUS', payload: 'completed' })
          addLog('Interview complete. Fetching results...', 'info')
          await fetchResults(sessionId)
        } else {
          dispatch({
            type: 'UPDATE_QUESTION',
            payload: {
              question: next_action.question,
              currentRound: next_action.current_round,
            },
          })
          addLog(`Next question — Round ${next_action.current_round}: ${next_action.question?.topic_area}`, 'info')
        }
      }

      return data
    } catch (err) {
      addLog(`Chunk upload failed: ${err.message}`, 'error')
      throw err
    }
  }, [state, addLog, fetchResults])

  const endInterview = useCallback(() => {
    dispatch({ type: 'SET_STATUS', payload: 'processing' })
    addLog('Ending interview...', 'info')
  }, [addLog])

  return {
    state,
    initSession,
    sendChunk,
    endInterview,
    fetchResults,
    addLog,
  }
}
