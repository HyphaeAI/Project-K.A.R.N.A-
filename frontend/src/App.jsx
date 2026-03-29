import { useInterviewState } from './hooks/useInterviewState'
import RoleSelect from './components/RoleSelect'
import WebcamPanel from './components/WebcamPanel'
import QuestionCard from './components/QuestionCard'
import TerminalLog from './components/TerminalLog'
import InterviewControls from './components/InterviewControls'
import RadarChart from './components/RadarChart'
import ScoreCards from './components/ScoreCards'
import TranscriptLog from './components/TranscriptLog'
import SummaryPanel from './components/SummaryPanel'

export default function App() {
  const { state, initSession, sendChunk, endInterview, fetchResults, addLog } = useInterviewState()

  const renderView = () => {
    switch (state.status) {
      case 'idle':
        return <RoleSelect onStart={initSession} />

      case 'initializing':
        return (
          <div className="loading-screen">
            <div className="spinner" />
            <p>Initializing interview...</p>
          </div>
        )

      case 'recording':
      case 'processing':
        return (
          <div className="interview-screen">
            <div className="interview-col interview-col--left">
              <WebcamPanel state={state} addLog={addLog} />
              <InterviewControls
                state={state}
                sendChunk={sendChunk}
                endInterview={endInterview}
                addLog={addLog}
              />
            </div>
            <div className="interview-col interview-col--center">
              <QuestionCard state={state} />
            </div>
            <div className="interview-col interview-col--right">
              <TerminalLog logs={state.terminalLogs} />
            </div>
          </div>
        )

      case 'completed':
        return (
          <div className="results-dashboard">
            <RadarChart results={state.finalResults} />
            <ScoreCards results={state.finalResults} />
            <SummaryPanel results={state.finalResults} />
            <TranscriptLog results={state.finalResults} roundHistory={state.roundHistory} />
          </div>
        )

      default:
        return null
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title">K.A.R.N.A.</h1>
      </header>
      <main className="app-main">
        {renderView()}
      </main>
    </div>
  )
}
