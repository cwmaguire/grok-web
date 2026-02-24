import { useEffect } from 'react'
import { useChatStore } from './stores/chatStore'
import OutputPane from './components/OutputPane'
import InputPane from './components/InputPane'
import IntermediatePane from './components/IntermediatePane'
import Sidebar from './components/Sidebar'

export default function App() {
  const { conversationId, loadConversations, createConversation } = useChatStore()

  useEffect(() => {
    loadConversations().then(() => {
      if (!useChatStore.getState().conversationId) {
        createConversation()
      }
    })
  }, [])

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '220px 1fr 1fr',
      gridTemplateRows: '1fr auto',
      height: '100vh',
      width: '100vw',
      background: '#0d1117',
      color: '#e6edf3',
    }}>
      {/* Sidebar */}
      <div style={{
        gridRow: '1 / 3',
        gridColumn: '1',
        borderRight: '1px solid #30363d',
        overflow: 'auto',
      }}>
        <Sidebar />
      </div>

      {/* Output pane - top center */}
      <div style={{
        gridRow: '1',
        gridColumn: '2',
        overflow: 'auto',
        padding: '16px',
        borderRight: '1px solid #30363d',
      }}>
        <OutputPane />
      </div>

      {/* Input pane - bottom center */}
      <div style={{
        gridRow: '2',
        gridColumn: '2',
        borderTop: '1px solid #30363d',
        borderRight: '1px solid #30363d',
        minHeight: '150px',
        maxHeight: '40vh',
      }}>
        <InputPane />
      </div>

      {/* Intermediate pane - right */}
      <div style={{
        gridRow: '1 / 3',
        gridColumn: '3',
        overflow: 'auto',
        padding: '16px',
      }}>
        <IntermediatePane />
      </div>
    </div>
  )
}
