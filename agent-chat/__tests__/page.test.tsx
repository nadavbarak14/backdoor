import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import ChatPage from '../app/page'

describe('ChatPage', () => {
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
    render(<ChatPage />)
    const input = screen.getByPlaceholderText('Ask about players, teams, stats...') as HTMLInputElement
    fireEvent.change(input, { target: { value: 'Who is the top scorer?' } })
    expect(input.value).toBe('Who is the top scorer?')
  })

  it('clicking quick prompt fills the input', () => {
    render(<ChatPage />)
    const topScorersBtn = screen.getByText('Top Scorers')
    fireEvent.click(topScorersBtn)
    const input = screen.getByPlaceholderText('Ask about players, teams, stats...') as HTMLInputElement
    expect(input.value).toBe('Who are the top scorers this season?')
  })

  it('submitting a message adds it to the chat', async () => {
    render(<ChatPage />)
    const input = screen.getByPlaceholderText('Ask about players, teams, stats...')
    const form = input.closest('form')!

    fireEvent.change(input, { target: { value: 'Test message' } })
    fireEvent.submit(form)

    await waitFor(() => {
      expect(screen.getByText('Test message')).toBeInTheDocument()
    })
  })

  it('clears input after submitting', async () => {
    render(<ChatPage />)
    const input = screen.getByPlaceholderText('Ask about players, teams, stats...') as HTMLInputElement
    const form = input.closest('form')!

    fireEvent.change(input, { target: { value: 'Test message' } })
    fireEvent.submit(form)

    await waitFor(() => {
      expect(input.value).toBe('')
    })
  })

  it('shows typing indicator after submitting', async () => {
    render(<ChatPage />)
    const input = screen.getByPlaceholderText('Ask about players, teams, stats...')
    const form = input.closest('form')!

    fireEvent.change(input, { target: { value: 'Test message' } })
    fireEvent.submit(form)

    await waitFor(() => {
      const typingIndicator = document.querySelector('.typing-indicator')
      expect(typingIndicator).toBeInTheDocument()
    })
  })

  it('receives AI response after submitting', async () => {
    render(<ChatPage />)
    const input = screen.getByPlaceholderText('Ask about players, teams, stats...')
    const form = input.closest('form')!

    fireEvent.change(input, { target: { value: 'Test message' } })
    fireEvent.submit(form)

    // Wait for the simulated AI response (1500ms delay in component)
    await waitFor(
      () => {
        expect(screen.getByText(/I'm ready to analyze basketball data/)).toBeInTheDocument()
      },
      { timeout: 3000 }
    )
  })

  it('does not submit empty messages', () => {
    render(<ChatPage />)
    const input = screen.getByPlaceholderText('Ask about players, teams, stats...')
    const form = input.closest('form')!

    fireEvent.submit(form)

    // Welcome state should still be visible
    expect(screen.getByText('READY TO ANALYZE')).toBeInTheDocument()
  })

  it('renders the footer info text', () => {
    render(<ChatPage />)
    expect(screen.getByText('Powered by advanced basketball analytics')).toBeInTheDocument()
  })
})
