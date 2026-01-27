import '@testing-library/jest-dom/vitest'
import { vi } from 'vitest'

// Mock scrollIntoView
Element.prototype.scrollIntoView = vi.fn()
