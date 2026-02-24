import { useEffect, useRef } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { useChatStore } from '../stores/chatStore'

export default function OutputPane() {
  const { messages, streamingContent, isStreaming } = useChatStore()
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  return (
    <div style={{ fontSize: '14px', lineHeight: '1.6' }}>
      {messages.map(msg => (
        <div key={msg.id} style={{
          marginBottom: '16px',
          padding: '8px 12px',
          borderRadius: '6px',
          background: msg.role === 'user' ? '#1c2333' : 'transparent',
        }}>
          <div style={{
            fontSize: '11px',
            color: '#8b949e',
            marginBottom: '4px',
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
          }}>
            {msg.role === 'user' ? 'You' : 'Grok'}
          </div>
          {msg.role === 'user' ? (
            <pre style={{
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              fontFamily: 'inherit',
              margin: 0,
            }}>{msg.content}</pre>
          ) : (
            <MarkdownContent content={msg.content || ''} />
          )}
        </div>
      ))}

      {/* Streaming content */}
      {isStreaming && streamingContent && (
        <div style={{ marginBottom: '16px', padding: '8px 12px' }}>
          <div style={{
            fontSize: '11px',
            color: '#8b949e',
            marginBottom: '4px',
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
          }}>
            Grok
          </div>
          <MarkdownContent content={streamingContent} />
          <span style={{
            display: 'inline-block',
            width: '8px',
            height: '16px',
            background: '#58a6ff',
            animation: 'blink 1s step-end infinite',
            marginLeft: '2px',
            verticalAlign: 'text-bottom',
          }} />
        </div>
      )}

      {isStreaming && !streamingContent && (
        <div style={{ color: '#8b949e', padding: '8px 12px', fontStyle: 'italic' }}>
          Thinking...
        </div>
      )}

      <div ref={bottomRef} />

      <style>{`
        @keyframes blink {
          50% { opacity: 0; }
        }
      `}</style>
    </div>
  )
}

function MarkdownContent({ content }: { content: string }) {
  return (
    <Markdown
      remarkPlugins={[remarkGfm]}
      components={{
        code({ className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || '')
          const isInline = !match && !String(children).includes('\n')

          if (isInline) {
            return (
              <code style={{
                background: '#1c2333',
                padding: '2px 6px',
                borderRadius: '4px',
                fontSize: '13px',
              }} {...props}>
                {children}
              </code>
            )
          }

          return (
            <SyntaxHighlighter
              style={oneDark}
              language={match ? match[1] : 'text'}
              PreTag="div"
              customStyle={{
                margin: '8px 0',
                borderRadius: '6px',
                fontSize: '13px',
              }}
            >
              {String(children).replace(/\n$/, '')}
            </SyntaxHighlighter>
          )
        },
        pre({ children }) {
          return <>{children}</>
        },
      }}
    >
      {content}
    </Markdown>
  )
}
