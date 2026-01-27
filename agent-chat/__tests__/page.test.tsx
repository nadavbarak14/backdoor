import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import ChatPage from '../app/page'

// Mock the useChat hook from @ai-sdk/react
const mockUseChat = vi.fn()
vi.mock('@ai-sdk/react', () => ({
  useChat: () => mockUseChat()
}))

// Default mock implementation
const createDefaultMock = (overrides = {}) => ({
  messages: [],
  input: '',
  setInput: vi.fn(),
  handleSubmit: vi.fn(),
  isLoading: false,
  setMessages: vi.fn(),
  ...overrides
})

describe('ChatPage', () => {
  beforeEach(() => {
    // Reset mock to default state before each test
    mockUseChat.mockReturnValue(createDefaultMock())
  })

  it('renders the BACKDOOR header', () => {
    render(<ChatPage />)
    expect(screen.getByText('BACKDOOR')).toBeInTheDocument()
  })

  it('renders the AI ANALYTICS subtitle', () => {
    render(<ChatPage />)
    expect(screen.getByText('AI ANALYTICS')).toBeInTheDocument()
  })

  it('renders the LIVE DATA indicator', () => {
    render(<ChatPage />)
    expect(screen.getByText('LIVE DATA')).toBeInTheDocument()
  })

  it('renders the welcome message when no messages exist', () => {
    render(<ChatPage />)
    expect(screen.getByText('READY TO ANALYZE')).toBeInTheDocument()
    expect(screen.getByText(/Ask me anything about basketball stats/)).toBeInTheDocument()
  })

  it('renders all quick prompt buttons', () => {
    render(<ChatPage />)
    expect(screen.getByText('Top Scorers')).toBeInTheDocument()
    expect(screen.getByText('Team Stats')).toBeInTheDocument()
    expect(screen.getByText('Live Games')).toBeInTheDocument()
    expect(screen.getByText('Hot Streaks')).toBeInTheDocument()
  })

  it('renders the input field with correct placeholder', () => {
    render(<ChatPage />)
    const input = screen.getByPlaceholderText('Ask about players, teams, stats...')
    expect(input).toBeInTheDocument()
  })

  it('renders the send button', () => {
    render(<ChatPage />)
    expect(screen.getByText('SEND')).toBeInTheDocument()
  })

  it('updates input value when typing', () => {
    const setInputMock = vi.fn()
    mockUseChat.mockReturnValue(createDefaultMock({ setInput: setInputMock }))

    render(<ChatPage />)
    const input = screen.getByPlaceholderText('Ask about players, teams, stats...') as HTMLInputElement
    fireEvent.change(input, { target: { value: 'Who is the top scorer?' } })
    expect(setInputMock).toHaveBeenCalledWith('Who is the top scorer?')
  })

  it('clicking quick prompt fills the input', () => {
    const setInputMock = vi.fn()
    mockUseChat.mockReturnValue(createDefaultMock({ setInput: setInputMock }))

    render(<ChatPage />)
    const topScorersBtn = screen.getByText('Top Scorers')
    fireEvent.click(topScorersBtn)
    expect(setInputMock).toHaveBeenCalledWith('Who are the top scorers this season?')
  })

  it('submitting a message displays it in the chat', async () => {
    // Set up mock with a user message already in the list
    mockUseChat.mockReturnValue(createDefaultMock({
      messages: [{ id: '1', role: 'user', content: 'Test message', createdAt: new Date() }]
    }))

    render(<ChatPage />)

    await waitFor(() => {
      expect(screen.getByText('Test message')).toBeInTheDocument()
    })
  })

  it('calls handleSubmit when form is submitted with input', () => {
    const handleSubmitMock = vi.fn()
    mockUseChat.mockReturnValue(createDefaultMock({
      input: 'Test message',
      handleSubmit: handleSubmitMock
    }))

    render(<ChatPage />)
    const input = screen.getByPlaceholderText('Ask about players, teams, stats...')
    const form = input.closest('form')!

    fireEvent.submit(form)

    expect(handleSubmitMock).toHaveBeenCalled()
  })

  it('shows typing indicator when loading', async () => {
    mockUseChat.mockReturnValue(createDefaultMock({
      messages: [{ id: '1', role: 'user', content: 'Test', createdAt: new Date() }],
      isLoading: true
    }))

    render(<ChatPage />)

    await waitFor(() => {
      const typingIndicator = document.querySelector('.typing-indicator')
      expect(typingIndicator).toBeInTheDocument()
    })
  })

  it('displays AI response from messages', async () => {
    mockUseChat.mockReturnValue(createDefaultMock({
      messages: [
        { id: '1', role: 'user', content: 'Test message', createdAt: new Date() },
        { id: '2', role: 'assistant', content: 'Here is the basketball analysis', createdAt: new Date() }
      ]
    }))

    render(<ChatPage />)

    await waitFor(() => {
      expect(screen.getByText('Here is the basketball analysis')).toBeInTheDocument()
    })
  })

  it('does not submit empty messages', () => {
    const handleSubmitMock = vi.fn()
    mockUseChat.mockReturnValue(createDefaultMock({
      input: '',
      handleSubmit: handleSubmitMock
    }))

    render(<ChatPage />)
    const input = screen.getByPlaceholderText('Ask about players, teams, stats...')
    const form = input.closest('form')!

    fireEvent.submit(form)

    // handleSubmit should not be called with empty input
    expect(handleSubmitMock).not.toHaveBeenCalled()
    // Welcome state should still be visible
    expect(screen.getByText('READY TO ANALYZE')).toBeInTheDocument()
  })

  it('renders the footer info text', () => {
    render(<ChatPage />)
    expect(screen.getByText('Powered by advanced basketball analytics')).toBeInTheDocument()
  })
})
