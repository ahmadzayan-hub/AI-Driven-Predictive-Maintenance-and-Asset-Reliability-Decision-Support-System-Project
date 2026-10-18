import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { DecisionActions } from './DecisionActions'

vi.mock('../../i18n', () => ({ useI18n: () => ({ t: (key: string) => key }) }))

describe('Decision Command Centre navigation', () => {
  it('triggers only existing, user-selected actions', () => {
    const onUpload = vi.fn(), onDashboard = vi.fn(), onApprovals = vi.fn()
    render(<DecisionActions onUpload={onUpload} onDashboard={onDashboard} onApprovals={onApprovals} />)
    fireEvent.click(screen.getByRole('button', { name: /decision.upload/ }))
    expect(onUpload).toHaveBeenCalledOnce()
    expect(onDashboard).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: /decision.dashboard/ }))
    fireEvent.click(screen.getByRole('button', { name: /decision.approvals/ }))
    expect(onDashboard).toHaveBeenCalledOnce()
    expect(onApprovals).toHaveBeenCalledOnce()
  })
})
