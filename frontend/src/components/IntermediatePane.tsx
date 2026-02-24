import { useEffect, useRef } from 'react'
import { useChatStore } from '../stores/chatStore'
import ToolCallCard from './ToolCallCard'

export default function IntermediatePane() {
  const { toolCalls, thinkingChunks, isStreaming, currentTurn } = useChatStore()
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [toolCalls, thinkingChunks])

  const hasContent = toolCalls.length > 0 || thinkingChunks.length > 0

  return (
    <div style={{ fontSize: '13px' }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '12px',
        paddingBottom: '8px',
        borderBottom: '1px solid #30363d',
      }}>
        <span style={{ color: '#8b949e', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          Activity
        </span>
        {isStreaming && (
          <span style={{
            color: '#d29922',
            fontSize: '12px',
          }}>
            Turn {currentTurn}
          </span>
        )}
      </div>

      {!hasContent && !isStreaming && (
        <div style={{ color: '#484f58', fontStyle: 'italic' }}>
          Tool calls and thinking will appear here...
        </div>
      )}

      {/* Thinking */}
      {thinkingChunks.length > 0 && (
        <div style={{
          marginBottom: '12px',
          padding: '8px 12px',
          background: '#1c1c3a',
          borderRadius: '6px',
          border: '1px solid #30365d',
        }}>
          <div style={{
            color: '#a371f7',
            fontSize: '11px',
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            marginBottom: '4px',
          }}>
            Thinking
          </div>
          <pre style={{
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            fontFamily: 'inherit',
            fontSize: '12px',
            color: '#c9d1d9',
            maxHeight: '300px',
            overflow: 'auto',
            margin: 0,
          }}>
            {thinkingChunks.map(c => c.content).join('')}
          </pre>
        </div>
      )}

      {/* Tool calls */}
      {toolCalls.map(tc => (
        <ToolCallCard key={tc.id} tc={tc} />
      ))}

      <div ref={bottomRef} />
    </div>
  )
}
