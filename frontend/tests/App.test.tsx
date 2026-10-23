import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../src/App'

// Mock fetch globally
global.fetch = vi.fn()

describe('App', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('renders title and description', () => {
    render(<App />)
    expect(screen.getByText('Beacon Lens')).toBeInTheDocument()
    expect(screen.getByText('AI/ML Knowledge Platform — RAG · Agent · Wiki')).toBeInTheDocument()
  })

  it('shows loading state initially', () => {
    render(<App />)
    expect(screen.getByText('Checking backend health...')).toBeInTheDocument()
  })

  it('displays backend health when fetch succeeds', async () => {
    ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        status: 'ok',
        version: '1.0.0',
        service: 'beacon-lens',
      }),
    })

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('● Online')).toBeInTheDocument()
      expect(screen.getByText(/beacon-lens.*v1\.0\.0/)).toBeInTheDocument()
      expect(screen.getByText('Status: ok')).toBeInTheDocument()
    })
  })

  it('displays error state when fetch fails', async () => {
    ;(fetch as unknown as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('Network error'))

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('Backend unreachable')).toBeInTheDocument()
      expect(screen.getByText('Network error')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
    })
  })

  it('displays workflow cards', async () => {
    ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        status: 'ok',
        version: '1.0.0',
        service: 'beacon-lens',
      }),
    })

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('RAG Query')).toBeInTheDocument()
      expect(screen.getByText('Wiki Generation')).toBeInTheDocument()
      expect(screen.getByText('Reasoning Agent')).toBeInTheDocument()
    })
  })

  it('shows footer with author info', async () => {
    ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        status: 'ok',
        version: '1.0.0',
        service: 'beacon-lens',
      }),
    })

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText(/Ryan Vo \| AI & Machine Learning/)).toBeInTheDocument()
      expect(screen.getByText('ryandtvo@gmail.com')).toBeInTheDocument()
    })
  })
})