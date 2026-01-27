import '@testing-library/jest-dom/vitest'

// Mock scrollIntoView
Element.prototype.scrollIntoView = vi.fn()
