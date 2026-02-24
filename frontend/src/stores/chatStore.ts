import { create } from 'zustand'

interface Conversation {
  id: string
  title: string
  created_at: string
  updated_at: string
}

interface Message {
  id: string
  role: 'user' | 'assistant' | 'tool'
  content: string | null
  tool_calls?: ToolCallData[]
}

interface ToolCallData {
  id: string
  name: string
  arguments: Record<string, unknown>
}

interface ToolCallEvent {
  id: string
  name: string
  arguments: Record<string, unknown>
  result?: string
  is_error?: boolean
  status: 'running' | 'done'
}

interface ThinkingChunk {
  content: string
}

interface ChatState {
  // Conversations
  conversations: Conversation[]
  conversationId: string | null

  // Messages for current conversation
  messages: Message[]

  // Streaming state
  streamingContent: string
  isStreaming: boolean
  currentTurn: number

  // Intermediate pane data
  toolCalls: ToolCallEvent[]
  thinkingChunks: ThinkingChunk[]

  // WebSocket
  ws: WebSocket | null

  // Actions
  loadConversations: () => Promise<void>
  createConversation: () => Promise<void>
  selectConversation: (id: string) => Promise<void>
  deleteConversation: (id: string) => Promise<void>
  sendMessage: (content: string) => void
  interrupt: () => void
  connectWs: (conversationId: string) => void
  disconnectWs: () => void
}

const API_BASE = '/api'

export const useChatStore = create<ChatState>((set, get) => ({
  conversations: [],
  conversationId: null,
  messages: [],
  streamingContent: '',
  isStreaming: false,
  currentTurn: 1,
  toolCalls: [],
  thinkingChunks: [],
  ws: null,

  loadConversations: async () => {
    const res = await fetch(`${API_BASE}/conversations`)
    const data = await res.json()
    set({ conversations: data })
  },

  createConversation: async () => {
    const res = await fetch(`${API_BASE}/conversations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: 'New Conversation' }),
    })
    const conv = await res.json()
    set(s => ({ conversations: [conv, ...s.conversations] }))
    get().selectConversation(conv.id)
  },

  selectConversation: async (id: string) => {
    get().disconnectWs()

    // Load messages
    const res = await fetch(`${API_BASE}/conversations/${id}/messages`)
    const msgs = await res.json()

    // Build display messages from DB messages
    const displayMessages: Message[] = []
    for (const msg of msgs) {
      if (msg.role === 'user' || (msg.role === 'assistant' && msg.content)) {
        displayMessages.push({
          id: msg.id,
          role: msg.role,
          content: msg.content,
          tool_calls: msg.tool_calls,
        })
      }
    }

    set({
      conversationId: id,
      messages: displayMessages,
      streamingContent: '',
      isStreaming: false,
      currentTurn: 1,
      toolCalls: [],
      thinkingChunks: [],
    })

    get().connectWs(id)
  },

  deleteConversation: async (id: string) => {
    await fetch(`${API_BASE}/conversations/${id}`, { method: 'DELETE' })
    const { conversationId, conversations } = get()
    const remaining = conversations.filter(c => c.id !== id)
    set({ conversations: remaining })

    if (conversationId === id) {
      if (remaining.length > 0) {
        get().selectConversation(remaining[0].id)
      } else {
        get().createConversation()
      }
    }
  },

  connectWs: (conversationId: string) => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/ws/${conversationId}`
    const ws = new WebSocket(wsUrl)

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      const state = get()

      switch (msg.type) {
        case 'text_delta':
          set({ streamingContent: state.streamingContent + msg.data.content })
          break

        case 'thinking':
          set({
            thinkingChunks: [
              ...state.thinkingChunks,
              { content: msg.data.content },
            ],
          })
          break

        case 'tool_call':
          set({
            toolCalls: [
              ...state.toolCalls,
              {
                id: msg.data.id,
                name: msg.data.name,
                arguments: msg.data.arguments,
                status: 'running',
              },
            ],
          })
          break

        case 'tool_result':
          set({
            toolCalls: state.toolCalls.map(tc =>
              tc.id === msg.data.id
                ? { ...tc, result: msg.data.result, is_error: msg.data.is_error, status: 'done' as const }
                : tc
            ),
          })
          break

        case 'turn_start':
          set({ currentTurn: msg.data.turn_number })
          break

        case 'done': {
          // Finalize streaming content as a message
          const content = state.streamingContent
          if (content) {
            set(s => ({
              messages: [...s.messages, {
                id: crypto.randomUUID(),
                role: 'assistant',
                content,
              }],
              streamingContent: '',
              isStreaming: false,
            }))
          } else {
            set({ isStreaming: false })
          }
          break
        }

        case 'cancelled':
          set({ isStreaming: false, streamingContent: '' })
          break

        case 'error':
          console.error('Agent error:', msg.data.message)
          set({ isStreaming: false })
          break
      }
    }

    ws.onclose = () => {
      set({ ws: null })
    }

    set({ ws })
  },

  disconnectWs: () => {
    const { ws } = get()
    if (ws) {
      ws.close()
      set({ ws: null })
    }
  },

  sendMessage: (content: string) => {
    const { ws, isStreaming } = get()
    if (!ws || isStreaming || ws.readyState !== WebSocket.OPEN) return

    // Add user message to display
    set(s => ({
      messages: [...s.messages, {
        id: crypto.randomUUID(),
        role: 'user',
        content,
      }],
      streamingContent: '',
      isStreaming: true,
      currentTurn: 1,
      toolCalls: [],
      thinkingChunks: [],
    }))

    ws.send(JSON.stringify({ type: 'user_message', content }))
  },

  interrupt: () => {
    const { ws } = get()
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'interrupt' }))
    }
  },
}))
