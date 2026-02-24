import { useEffect, useRef, useCallback } from 'react'
import { EditorView, keymap } from '@codemirror/view'
import { EditorState } from '@codemirror/state'
import { markdown } from '@codemirror/lang-markdown'
import { vim } from '@replit/codemirror-vim'
import { useChatStore } from '../stores/chatStore'

const theme = EditorView.theme({
  '&': {
    backgroundColor: '#0d1117',
    color: '#e6edf3',
    height: '100%',
    fontSize: '14px',
    fontFamily: "'SF Mono', 'Menlo', 'Monaco', 'Consolas', monospace",
  },
  '.cm-content': {
    padding: '12px',
    caretColor: '#58a6ff',
  },
  '.cm-cursor': {
    borderLeftColor: '#58a6ff',
  },
  '.cm-gutters': {
    display: 'none',
  },
  '&.cm-focused .cm-selectionBackground, .cm-selectionBackground': {
    backgroundColor: '#264f78 !important',
  },
  '.cm-vim-panel': {
    backgroundColor: '#161b22',
    color: '#8b949e',
    padding: '2px 8px',
    fontSize: '12px',
  },
})

export default function InputPane() {
  const containerRef = useRef<HTMLDivElement>(null)
  const viewRef = useRef<EditorView | null>(null)
  const { sendMessage, interrupt, isStreaming } = useChatStore()

  const handleSubmit = useCallback(() => {
    const view = viewRef.current
    if (!view) return

    const content = view.state.doc.toString().trim()
    if (!content) return

    sendMessage(content)

    // Clear editor
    view.dispatch({
      changes: { from: 0, to: view.state.doc.length, insert: '' },
    })
  }, [sendMessage])

  useEffect(() => {
    if (!containerRef.current) return

    const submitKeymap = keymap.of([{
      key: 'Ctrl-Enter',
      run: () => {
        handleSubmit()
        return true
      },
    }, {
      key: 'Mod-Enter',
      run: () => {
        handleSubmit()
        return true
      },
    }])

    const state = EditorState.create({
      doc: '',
      extensions: [
        vim(),
        submitKeymap,
        markdown(),
        theme,
        EditorView.lineWrapping,
        EditorState.tabSize.of(2),
      ],
    })

    const view = new EditorView({
      state,
      parent: containerRef.current,
    })

    viewRef.current = view

    return () => {
      view.destroy()
      viewRef.current = null
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Status bar */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '4px 12px',
        background: '#161b22',
        borderBottom: '1px solid #30363d',
        fontSize: '12px',
        color: '#8b949e',
      }}>
        <span>vim mode | Ctrl+Enter to send</span>
        {isStreaming && (
          <button
            onClick={interrupt}
            style={{
              background: '#da3633',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              padding: '2px 10px',
              cursor: 'pointer',
              fontSize: '12px',
              fontFamily: 'inherit',
            }}
          >
            Interrupt
          </button>
        )}
      </div>

      {/* Editor */}
      <div
        ref={containerRef}
        style={{ flex: 1, overflow: 'auto' }}
      />
    </div>
  )
}
