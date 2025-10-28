import { Box, Flex, Heading, IconButton, Text, useColorMode, useDisclosure, Button, HStack } from '@chakra-ui/react'
import { MoonIcon, SunIcon } from '@chakra-ui/icons'
import Chat from './components/Chat'
import TemplateSwitcher from './components/TemplateSwitcher'

export default function App() {
  const { colorMode, toggleColorMode } = useColorMode()

  return (
    <Flex direction="column" minH="100vh">
      <Flex as="header" align="center" justify="space-between" px={6} py={3} borderBottom="1px" borderColor="whiteAlpha.200">
        <HStack spacing={4}>
          <Heading size="md">OwOGPT</Heading>
          <Text fontSize="sm" color="whiteAlpha.700">A modern, fast GPT chat UI</Text>
        </HStack>
        <HStack>
          <TemplateSwitcher />
          <IconButton aria-label="toggle theme" onClick={toggleColorMode} icon={colorMode === 'dark' ? <SunIcon /> : <MoonIcon />} variant="ghost" />
        </HStack>
      </Flex>
      <Box flex="1" overflow="hidden">
        <Chat />
      </Box>
      <Box as="footer" fontSize="xs" opacity={0.7} textAlign="center" py={2}>
        <Text>Powered by OwOGPT • MQTT/OpenAI/Ollama</Text>
      </Box>
    </Flex>
  )
}


