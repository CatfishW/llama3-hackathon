import { useEffect, useRef, useState } from 'react'
import { Box, Flex, HStack, IconButton, Input, Menu, MenuButton, MenuItem, MenuList, Spinner, Text, VStack } from '@chakra-ui/react'
import { ArrowUpIcon, AddIcon, DeleteIcon, ChevronDownIcon } from '@chakra-ui/icons'
import { ChatMessage, ChatSession, createSession, getMessages, listSessions, sendMessage, deleteSession } from '../api'

export default function Chat() {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [current, setCurrent] = useState<ChatSession | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  // SSE optional: not used for content right now; REST returns final message reliably.

  useEffect(() => {
    ;(async () => {
      const s = await listSessions()
      setSessions(s)
      if (s.length) {
        setCurrent(s[0])
      } else {
        // Check if user has a saved template preference
        const savedTemplateId = localStorage.getItem('owogpt_selected_template')
        if (savedTemplateId) {
          // Create session with saved template
          const created = await createSession('New Chat')
          setSessions([created])
          setCurrent(created)
          
          // Apply saved template to new session
          try {
            const { data: templates } = await api.get('/templates/')
            const template = templates.find((t: any) => t.id === Number(savedTemplateId))
            if (template) {
              await api.patch(`/chat/sessions/${created.id}`, {
                template_id: Number(savedTemplateId),
                system_prompt: template.content
              })
            }
          } catch {}
        } else {
          // No preference, create default session
          const created = await createSession('New Chat')
          setSessions([created])
          setCurrent(created)
        }
      }
    })()
  }, [])

  useEffect(() => {
    if (!current) return
    ;(async () => {
      const msgs = await getMessages(current.id)
      setMessages(msgs)
    })()
  }, [current])

  const listRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  function append(role: 'user' | 'assistant', content: string) {
    if (!current) return
    const temp: ChatMessage = {
      id: Math.floor(Math.random() * 1e9),
      session_id: current.id,
      role,
      content,
      created_at: new Date().toISOString(),
      request_id: undefined,
    }
    setMessages(prev => [...prev, temp])
  }


  async function handleSend() {
    if (!current || !input.trim()) return
    const content = input
    setInput('')
    append('user', content)
    setLoading(true)
    try {
      const resp = await sendMessage(current.id, content)
      // resp contains session, user_message, assistant_message
      const assistant = resp?.assistant_message
      if (assistant?.content) append('assistant', assistant.content)
    } finally {
      setLoading(false)
    }
  }

  async function handleNewSession() {
    const created = await createSession('New Chat')
    setSessions([created, ...sessions])
    setCurrent(created)
    setMessages([])
  }

  async function handleDeleteSession(id: number) {
    if (!confirm('Delete this session?')) return
    try {
      await deleteSession(id)
      const updated = sessions.filter(s => s.id !== id)
      setSessions(updated)
      if (current?.id === id) {
        setCurrent(updated[0] || null)
      }
    } catch {}
  }

  return (
    <Flex h="calc(100vh - 100px)">
      <Box w="280px" borderRight="1px" borderColor="whiteAlpha.200" p={3} overflowY="auto">
        <HStack justify="space-between" mb={3}>
          <Text fontWeight="bold">Chats</Text>
          <IconButton aria-label="new" size="sm" icon={<AddIcon />} onClick={handleNewSession} />
        </HStack>
        <VStack align="stretch" spacing={2}>
          {sessions.map(s => (
            <HStack key={s.id} p={2} borderRadius="md" bg={current?.id === s.id ? 'whiteAlpha.200' : 'transparent'} _hover={{ bg: 'whiteAlpha.100' }} cursor="pointer" onClick={() => setCurrent(s)}>
              <Box flex="1">
                <Text noOfLines={1}>{s.title}</Text>
                <Text fontSize="xs" opacity={0.6}>{new Date(s.updated_at).toLocaleString()}</Text>
              </Box>
              <Menu>
                <MenuButton as={IconButton} size="xs" icon={<ChevronDownIcon />} variant="ghost" onClick={(e) => e.stopPropagation()} />
                <MenuList>
                  <MenuItem icon={<DeleteIcon />} onClick={(e) => { e.stopPropagation(); handleDeleteSession(s.id) }}>Delete</MenuItem>
                </MenuList>
              </Menu>
            </HStack>
          ))}
        </VStack>
      </Box>
      <Flex flex="1" direction="column">
        <Box ref={listRef} flex="1" overflowY="auto" p={4}>
          <VStack align="stretch" spacing={3}>
            {messages.map(m => (
              <Box key={`${m.id}-${m.created_at}`} alignSelf={m.role === 'user' ? 'flex-end' : 'flex-start'} maxW="70%" p={3} borderRadius="lg" bg={m.role === 'user' ? 'blue.500' : 'whiteAlpha.200'}>
                <Text whiteSpace="pre-wrap">{m.content}</Text>
              </Box>
            ))}
          </VStack>
        </Box>
        <HStack p={3} borderTop="1px" borderColor="whiteAlpha.200">
          <Input placeholder="Send a message" value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }} />
          <IconButton aria-label="send" icon={loading ? <Spinner size="sm" /> : <ArrowUpIcon />} onClick={handleSend} isDisabled={loading || !input.trim()} />
        </HStack>
      </Flex>
    </Flex>
  )
}


