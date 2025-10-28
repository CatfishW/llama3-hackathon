import { useEffect, useState } from 'react'
import { Button, HStack, IconButton, Menu, MenuButton, MenuItem, MenuList, Modal, ModalBody, ModalCloseButton, ModalContent, ModalFooter, ModalHeader, ModalOverlay, Select, Textarea, useDisclosure, VStack, Input, Text } from '@chakra-ui/react'
import { AddIcon, EditIcon, DeleteIcon } from '@chakra-ui/icons'
import { Template, listTemplates, createTemplate, updateTemplate, deleteTemplate } from '../api'
import { api } from '../api'

const TEMPLATE_STORAGE_KEY = 'owogpt_selected_template'

export default function TemplateSwitcher() {
  const [templates, setTemplates] = useState<Template[]>([])
  const [value, setValue] = useState<string>('')
  const [editingTemplate, setEditingTemplate] = useState<Template | null>(null)
  const [newTitle, setNewTitle] = useState('')
  const [newContent, setNewContent] = useState('')
  const [newDescription, setNewDescription] = useState('')
  const { isOpen, onOpen, onClose } = useDisclosure()

  async function loadTemplates() {
    const t = await listTemplates()
    setTemplates(t)
    
    // Restore saved template preference
    const savedTemplateId = localStorage.getItem(TEMPLATE_STORAGE_KEY)
    if (savedTemplateId) {
      const exists = t.find(tpl => tpl.id === Number(savedTemplateId))
      if (exists) {
        setValue(savedTemplateId)
      }
    }
  }

  useEffect(() => {
    loadTemplates()
  }, [])

  async function applyTemplate(id: string) {
    setValue(id)
    // Save template preference to localStorage
    localStorage.setItem(TEMPLATE_STORAGE_KEY, id)
    
    try {
      const { data: sessions } = await api.get('/chat/sessions')
      if (sessions?.length) {
        const session = sessions[0]
        const template = templates.find(t => t.id === Number(id))
        if (template) {
          // Update session with new template and system prompt
          await api.patch(`/chat/sessions/${session.id}`, { 
            template_id: Number(id),
            system_prompt: template.content
          })
          // Reload page to clear message history display
          window.location.reload()
        }
      }
    } catch {}
  }

  function openCreateModal() {
    setEditingTemplate(null)
    setNewTitle('')
    setNewContent('')
    setNewDescription('')
    onOpen()
  }

  function openEditModal(t: Template) {
    setEditingTemplate(t)
    setNewTitle(t.title)
    setNewContent(t.content)
    setNewDescription(t.description || '')
    onOpen()
  }

  async function handleSave() {
    try {
      if (editingTemplate) {
        await updateTemplate(editingTemplate.id, { title: newTitle, content: newContent, description: newDescription })
      } else {
        await createTemplate(newTitle, newContent, newDescription)
      }
      await loadTemplates()
      onClose()
    } catch {}
  }

  async function handleDelete(id: number) {
    if (confirm('Delete this template?')) {
      try {
        await deleteTemplate(id)
        await loadTemplates()
      } catch {}
    }
  }

  return (
    <>
      <HStack>
        <Select size="sm" w="200px" placeholder="Template" value={value} onChange={(e) => applyTemplate(e.target.value)}>
          {templates.map(t => (
            <option key={t.id} value={t.id}>{t.title}</option>
          ))}
        </Select>
        <Menu>
          <MenuButton as={IconButton} size="sm" icon={<EditIcon />} variant="ghost" aria-label="Manage templates" />
          <MenuList>
            <MenuItem icon={<AddIcon />} onClick={openCreateModal}>New Template</MenuItem>
            {templates.map(t => (
              <MenuItem key={t.id} onClick={() => openEditModal(t)}>
                <HStack justify="space-between" w="full">
                  <Text>{t.title}</Text>
                  <IconButton size="xs" icon={<DeleteIcon />} aria-label="Delete" onClick={(e) => { e.stopPropagation(); handleDelete(t.id) }} />
                </HStack>
              </MenuItem>
            ))}
          </MenuList>
        </Menu>
      </HStack>

      <Modal isOpen={isOpen} onClose={onClose} size="xl">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>{editingTemplate ? 'Edit Template' : 'New Template'}</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={3}>
              <Input placeholder="Title" value={newTitle} onChange={(e) => setNewTitle(e.target.value)} />
              <Input placeholder="Description (optional)" value={newDescription} onChange={(e) => setNewDescription(e.target.value)} />
              <Textarea placeholder="System Prompt" rows={8} value={newContent} onChange={(e) => setNewContent(e.target.value)} />
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onClose}>Cancel</Button>
            <Button colorScheme="blue" onClick={handleSave}>Save</Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </>
  )
}


