import { useChatStore } from '../stores/chatStore'

export default function Sidebar() {
  const {
    conversations,
    conversationId,
    selectConversation,
    createConversation,
    deleteConversation,
  } = useChatStore()

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      background: '#010409',
    }}>
      {/* Header */}
      <div style={{
        padding: '12px',
        borderBottom: '1px solid #30363d',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <span style={{ fontWeight: 600, fontSize: '14px' }}>grok-web</span>
        <button
          onClick={() => createConversation()}
          style={{
            background: '#238636',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            padding: '4px 10px',
            cursor: 'pointer',
            fontSize: '12px',
            fontFamily: 'inherit',
          }}
        >
          + New
        </button>
      </div>

      {/* Conversation list */}
      <div style={{ flex: 1, overflow: 'auto', padding: '8px' }}>
        {conversations.map(conv => (
          <div
            key={conv.id}
            onClick={() => selectConversation(conv.id)}
            style={{
              padding: '8px 10px',
              borderRadius: '6px',
              marginBottom: '2px',
              cursor: 'pointer',
              background: conv.id === conversationId ? '#1c2333' : 'transparent',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              fontSize: '13px',
              color: conv.id === conversationId ? '#e6edf3' : '#8b949e',
            }}
          >
            <span style={{
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              flex: 1,
            }}>
              {conv.title}
            </span>
            <button
              onClick={(e) => {
                e.stopPropagation()
                deleteConversation(conv.id)
              }}
              style={{
                background: 'none',
                border: 'none',
                color: '#484f58',
                cursor: 'pointer',
                fontSize: '14px',
                padding: '0 4px',
                marginLeft: '4px',
                fontFamily: 'inherit',
              }}
            >
              x
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
