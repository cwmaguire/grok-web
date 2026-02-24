import { useState } from 'react'

interface ToolCallEvent {
  id: string
  name: string
  arguments: Record<string, unknown>
  result?: string
  is_error?: boolean
  status: 'running' | 'done'
}

export default function ToolCallCard({ tc }: { tc: ToolCallEvent }) {
  const [expanded, setExpanded] = useState(false)

  const statusColor = tc.status === 'running'
    ? '#d29922'
    : tc.is_error
      ? '#da3633'
      : '#3fb950'

  return (
    <div style={{
      border: `1px solid ${statusColor}33`,
      borderRadius: '6px',
      marginBottom: '8px',
      background: '#161b22',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '8px 12px',
          cursor: 'pointer',
          fontSize: '13px',
        }}
      >
        <span style={{ color: statusColor, fontWeight: 600 }}>
          {tc.status === 'running' ? '...' : tc.is_error ? 'x' : '✓'}
        </span>
        <span style={{ color: '#58a6ff', fontWeight: 500 }}>{tc.name}</span>
        <span style={{
          color: '#8b949e',
          fontSize: '12px',
          marginLeft: 'auto',
        }}>
          {expanded ? '▾' : '▸'}
        </span>
      </div>

      {/* Expanded content */}
      {expanded && (
        <div style={{
          borderTop: '1px solid #30363d',
          padding: '8px 12px',
          fontSize: '12px',
        }}>
          {/* Arguments */}
          <div style={{ marginBottom: '8px' }}>
            <div style={{ color: '#8b949e', marginBottom: '4px' }}>Arguments:</div>
            <pre style={{
              background: '#0d1117',
              padding: '8px',
              borderRadius: '4px',
              overflow: 'auto',
              maxHeight: '200px',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              margin: 0,
            }}>
              {JSON.stringify(tc.arguments, null, 2)}
            </pre>
          </div>

          {/* Result */}
          {tc.result !== undefined && (
            <div>
              <div style={{
                color: tc.is_error ? '#da3633' : '#8b949e',
                marginBottom: '4px',
              }}>
                {tc.is_error ? 'Error:' : 'Result:'}
              </div>
              <pre style={{
                background: '#0d1117',
                padding: '8px',
                borderRadius: '4px',
                overflow: 'auto',
                maxHeight: '300px',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                margin: 0,
                color: tc.is_error ? '#f85149' : '#e6edf3',
              }}>
                {tc.result}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
