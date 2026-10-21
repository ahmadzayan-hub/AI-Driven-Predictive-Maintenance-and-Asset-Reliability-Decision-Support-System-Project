import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { DecisionActions } from './DecisionActions'

describe('Decision Command Centre navigation', () => {
  it('triggers only existing, user-selected actions', () => {
    const onUpload = vi.fn(), onDashboard = vi.fn(), onApprovals = vi.fn(), onAgents = vi.fn()
    render(<DecisionActions onUpload={onUpload} onDashboard={onDashboard} onApprovals={onApprovals} onAgents={onAgents} />)
    fireEvent.click(screen.getByRole('button', { name: /Analyze a dataset/ }))
    expect(onUpload).toHaveBeenCalledOnce()
    expect(onDashboard).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: /Explore a dashboard/ }))
    fireEvent.click(screen.getByRole('button', { name: /Review decisions/ }))
    fireEvent.click(screen.getByRole('button', { name: /Inspect agent workflow/ }))
    expect(onDashboard).toHaveBeenCalledOnce()
    expect(onApprovals).toHaveBeenCalledOnce()
    expect(onAgents).toHaveBeenCalledOnce()
  })

  it('offers no upload in a read-only workspace or workflow without a run', () => {
    render(<DecisionActions onDashboard={vi.fn()} />)
    expect(screen.queryByRole('button', { name: /Analyze a dataset/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Inspect agent workflow/ })).not.toBeInTheDocument()
    expect(screen.getAllByRole('button')).toHaveLength(1)
  })
})
