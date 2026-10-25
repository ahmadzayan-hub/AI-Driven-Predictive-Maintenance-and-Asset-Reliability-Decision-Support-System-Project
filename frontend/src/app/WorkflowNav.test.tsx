import { fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { applyLocale } from '../i18n'
import type { Tab } from './routing'
import { parseRoute } from './routing'
import { WorkflowNav } from './WorkflowNav'

afterEach(() => applyLocale('en'))
for (const locale of ['en', 'ar'] as const) describe(`task navigation ${locale}`, () => {
  it('offers four ordered stages, a separate assistant, and contextual routes without mutation', () => {
    applyLocale(locale)
    const go = vi.fn()
    const view = render(<WorkflowNav tab="datasets" demo={false} onGo={go} />)
    expect(view.container.querySelectorAll('[data-route="overview"]')).toHaveLength(1)
    fireEvent.click(view.container.querySelector('[data-route="overview"]')!)
    expect(go).toHaveBeenCalledWith('overview')
    go.mockClear()
    const stages = [...view.container.querySelectorAll('.workflow-stage__entry')]
    expect(stages).toHaveLength(4)
    stages.forEach(button => fireEvent.click(button))
    expect(go.mock.calls).toEqual([['datasets'], ['runs'], ['approvals'], ['dashboard']])
    expect(stages[0]).toHaveAttribute('aria-current', 'step')
    expect(stages[1]).not.toHaveAttribute('aria-current')
    // Stage numbers are positions, not completed/approved status indicators.
    expect(view.container.querySelectorAll('.workflow-stage__entry[aria-current]')).toHaveLength(1)
    expect(view.container.querySelector('.workflow-stage__views')).not.toBeVisible()
    const routes: Tab[] = []
    for (const tab of ['runs', 'approvals'] as Tab[]) {
      view.rerender(<WorkflowNav tab={tab} demo={false} onGo={id => routes.push(id)} />)
      const context = view.container.querySelector('.workflow-stage__views:not([hidden])') as HTMLElement
      within(context).getAllByRole('button').forEach(button => fireEvent.click(button))
    }
    expect(routes).toEqual(['runs', 'assets', 'rmd', 'approvals', 'operations'])
    expect(parseRoute('#/assistant').tab).toBe('chat')
    expect(parseRoute('#/dashboard/kept-report/overview?site=A').runId).toBe('kept-report')
    view.rerender(<WorkflowNav tab="memory" demo={false} onGo={go} />)
    expect(view.container.querySelector('details')).toHaveAttribute('open')
    expect(view.container.querySelector('button[aria-current="page"]')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: locale === 'en' ? 'Ask Miyaar' : 'اسأل معيار' })).toBeInTheDocument()
  })
  it('keeps session-only functions out of the read-only demo', () => {
    applyLocale(locale)
    const go = vi.fn()
    const view = render(<WorkflowNav tab="overview" demo onGo={go} />)
    expect(screen.queryByRole('button', { name: locale === 'en' ? 'Ask Miyaar' : 'اسأل معيار' })).toBeNull()
    view.container.querySelectorAll('button').forEach(button => fireEvent.click(button))
    expect(go.mock.calls.flat()).not.toContain('operations')
    expect(go.mock.calls.flat()).not.toContain('memory')
    expect(go.mock.calls.flat()).not.toContain('preferences')
  })
})
