import { act, fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { applyLocale } from '../i18n'
import { MaintenancePreview } from '../features/maintenance/MaintenancePreview'
import { SAMPLE_ASSETS, summarize } from '../features/maintenance/sample'

beforeEach(() => {
  applyLocale('en')
  vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() })))
})
afterEach(() => {
  act(() => applyLocale('en'))
  delete document.documentElement.dataset.theme
  localStorage.clear()
  vi.unstubAllGlobals()
})

describe('maintenance preview', () => {
  it('uses operating-hour denominators, selected months and no invented empty availability', () => {
    const north = summarize(SAMPLE_ASSETS.filter((asset) => asset.site === 'north'), 'current')
    expect(north.downtime).toBe(88)
    expect(north.availability).toBeCloseTo(95.4166667)
    expect(north.cost).toBe(21320)
    expect(north.attention).toBe(2)
    expect(north.series).toEqual([{ month: '2026-07', value: 28 }, { month: '2026-08', value: 29 }, { month: '2026-09', value: 31 }])
    expect(summarize([], 'all').availability).toBeNull()
  })

  it('updates cards, chart data, evidence and cost with the same global filters', async () => {
    const user = userEvent.setup()
    render(<MaintenancePreview />)
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'PMP-101' } })
    expect(screen.getByText('86.9%')).toBeVisible()
    expect(screen.getByText('63 h')).toBeVisible()
    expect(screen.getByText('12,915 USD')).toBeVisible()
    expect(screen.getByText(/accounts for 100.0%/)).toBeVisible()
    await user.selectOptions(screen.getByLabelText('Reporting period'), 'previous')
    expect(screen.getByText('37 h')).toBeVisible()
    expect(screen.getByText('92.3%')).toBeVisible()
    await user.click(screen.getByText('View chart data'))
    expect(screen.getByRole('cell', { name: '14' })).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Review record PMP-101' }))
    expect(within(screen.getByRole('dialog')).getByText('37 h')).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Close evidence' }))
    await user.click(screen.getByRole('button', { name: 'Cost & exposure' }))
    expect(screen.getByRole('cell', { name: '8,105' })).toBeVisible()
  }, 15_000)

  it('shows a recoverable empty scope rather than misleading zero performance', async () => {
    const user = userEvent.setup()
    render(<MaintenancePreview />)
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'missing' } })
    expect(screen.getByRole('heading', { name: 'No equipment matches these filters.' })).toBeVisible()
    expect(screen.queryByRole('heading', { name: 'Availability' })).not.toBeInTheDocument()
    await user.click(screen.getAllByRole('button', { name: 'Reset filters' })[0])
    expect(screen.getByText('12 sample equipment records')).toBeVisible()
  })

  it('keeps reviews local and returns focus when a reviewed queue row is removed', async () => {
    const user = userEvent.setup()
    const fetch = vi.fn()
    vi.stubGlobal('fetch', fetch)
    render(<MaintenancePreview />)
    await user.click(screen.getByRole('button', { name: 'Maintenance reviews' }))
    await user.click(screen.getByRole('button', { name: 'Review record PMP-101' }))
    expect(screen.getByRole('dialog')).toHaveFocus()
    await user.click(screen.getByRole('button', { name: 'Mark reviewed in preview' }))
    expect(screen.getByRole('button', { name: 'Mark reviewed in preview' })).toBeDisabled()
    await user.click(screen.getByRole('button', { name: 'Close evidence' }))
    expect(screen.queryByRole('button', { name: 'Review record PMP-101' })).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1 })).toHaveFocus()
    expect(fetch).not.toHaveBeenCalled()
  })

  it('restores the surviving opener on Escape and never fabricates model performance', async () => {
    const user = userEvent.setup()
    render(<MaintenancePreview />)
    const opener = screen.getByRole('button', { name: 'Review record PMP-101' })
    await user.click(opener)
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(opener).toHaveFocus()
    await user.click(screen.getByRole('button', { name: 'Model evidence' }))
    expect(screen.getByRole('heading', { name: 'No evaluated model connected' })).toBeVisible()
    expect(screen.getByRole('link', { name: /Open model analyses/ })).toHaveAttribute('href', './#/runs')
  })

  it('switches the complete preview to Arabic and searches localized equipment types', async () => {
    const user = userEvent.setup()
    render(<MaintenancePreview />)
    await user.click(screen.getByRole('button', { name: 'Change language' }))
    expect(document.documentElement).toHaveAttribute('dir', 'rtl')
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('رؤية واضحة')
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'مضخة' } })
    expect(screen.getByText('3 سجلًا لمعدات تجريبية')).toBeVisible()
    expect(screen.getByRole('button', { name: 'مراجعة السجل PMP-101' })).toBeVisible()
  })
})
