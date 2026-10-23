import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { applyLocale } from '../../i18n'
import { OperationsView } from './OperationsView'
import { ValidationPanel } from './ValidationPanel'
import type { OperationsOverview, WorkOrder } from './types'

const org = { id: 'org-1', name: 'North plant', version: 1, role: 'owner' as const }
const site = { id: 'site-1', name: 'Pump station', code: 'PS' }
const asset = { id: 'asset-1', site_id: site.id, external_id: 'P-10', source_system: 'CMMS', name: 'Cooling pump', criticality: 'high' as const }
function overview(): OperationsOverview {
  return { principal_subject: 'local', organization: { ...org }, sites: [{ ...site }], assets: [{ ...asset }], members: [{ subject: 'local', role: 'owner' }], work_orders: [], work_order_count: 0, work_orders_truncated: false, permissions: { read: true, write: true, manage: true, authorize: true } }
}
function workOrder(): WorkOrder {
  return { id: 'wo-1', asset_id: asset.id, title: 'Inspect pump bearing', rationale: 'Review recorded vibration findings', priority: 'high', status: 'draft', assignee: 'local', due_date: '2026-11-01', version: 1,
    evidence: { run_id: 'run-1', asset_column: 'Asset_ID', source_asset_id: 'P-10', matching_records: 4, dataset_sha256: 'fixture-hash', captured_at: '2026-10-21T10:00:00Z', run_updated_at: '2026-10-21T10:00:00Z' }, completion: {}, audit: [] }
}
type Call = { path: string; method: string; body: Record<string, unknown>; language: string | null }
function serve(state = overview(), intercept?: (call: Call) => { status: number; body?: unknown } | 'offline' | undefined) {
  const calls: Call[] = []
  const response = (body: unknown, status = 200) => ({ ok: status >= 200 && status < 300, status, json: async () => structuredClone(body) } as Response)
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    const parsed = new URL(url, 'http://localhost')
    const call = { path: parsed.pathname, language: parsed.searchParams.get('language'), method: init?.method ?? 'GET', body: init?.body ? JSON.parse(String(init.body)) as Record<string, unknown> : {} }
    calls.push(call)
    const result = intercept?.(call)
    if (result === 'offline') throw new TypeError('network unavailable')
    if (result) return response(result.body ?? { detail: 'Conflict' }, result.status)
    if (call.path === '/api/runs') return response({ runs: [{ id: 'run-1', goal: 'Pump review', state: 'completed' }] })
    if (call.path === '/api/operations/organizations') return response(call.method === 'POST' ? state.organization : { organizations: [state.organization] })
    if (call.path.endsWith('/overview')) return response(state)
    if (call.path.endsWith('/sites')) { state.sites.push({ ...site, ...call.body } as typeof site); return response(state.sites.at(-1)) }
    if (call.path.endsWith('/assets')) { state.assets.push({ ...asset, ...call.body } as typeof asset); return response(state.assets.at(-1)) }
    if (call.path.endsWith('/members')) { state.organization.version++; return response({ ...call.body }) }
    if (call.path.endsWith('/work-orders')) { const order = { ...workOrder(), ...call.body } as WorkOrder; state.work_orders.push(order); state.work_order_count++; return response(order) }
    if (call.method === 'PATCH') {
      const order = state.work_orders[0]
      Object.assign(order, call.body, { version: order.version + 1 })
      order.audit.push({ id: String(order.version), action: `work_${order.status}`, actor: 'local', created_at: '2026-10-21T10:00:00Z', version: order.version, detail: {} })
      return response(order)
    }
    return response({}, 404)
  }))
  return { calls, state }
}

afterEach(() => { applyLocale('en', false); vi.unstubAllGlobals(); vi.restoreAllMocks() })

async function openDraft(user: ReturnType<typeof userEvent.setup>) {
  await screen.findByText('Records received')
  await user.click(screen.getByText('Create work order draft'))
  await user.selectOptions(screen.getByLabelText('Registered asset'), asset.id)
  await user.type(screen.getByLabelText('Work title'), 'Inspect pump bearing')
  await user.type(screen.getByLabelText('Why this work is needed'), 'Review recorded vibration findings')
  await user.type(screen.getByLabelText('Evidence run ID'), 'run-1')
  await user.selectOptions(screen.getByLabelText('Assigned team member'), 'local')
  fireEvent.change(screen.getByLabelText('Due date'), { target: { value: '2026-11-01' } })
}

describe('maintenance operations', () => {
  it('prefills only the exact revalidated source and never creates work on navigation', async () => {
    const { calls } = serve(overview(), call => call.path === '/api/runs/source-1' ? { status: 200, body: { id: 'source-1', goal: 'Selected source', state: 'awaiting_approval', dataset_id: 'dataset-7' } } : undefined)
    render(<OperationsView sourceRunId="source-1" onOpenRun={vi.fn()} />)
    expect(await screen.findByText('Selected source')).toBeInTheDocument()
    expect(await screen.findByLabelText('Evidence run ID')).toHaveValue('source-1')
    expect(screen.getByLabelText('Evidence run ID')).toHaveAttribute('readonly')
    expect(screen.getByLabelText('Asset column in the dataset')).toHaveValue('')
    expect(screen.getByLabelText('Registered asset')).toHaveValue('')
    expect(screen.getByLabelText('Assigned team member')).toHaveValue('')
    expect(calls.every(call => call.method === 'GET')).toBe(true)
    expect(screen.getByText(/Base dataset only/)).toBeInTheDocument()
  })
  it('clears prior prefill when the selected source changes or context is removed', async () => {
    serve(overview(), call => call.path === '/api/runs/source-1' ? { status: 200, body: { id: 'source-1', goal: 'First source', state: 'completed', dataset_id: 'dataset-7' } } : call.path === '/api/runs/source-2' ? { status: 404 } : undefined)
    const props = { onOpenRun: vi.fn(), onClearSource: vi.fn() }
    const view = render(<OperationsView {...props} sourceRunId="source-1" />)
    await screen.findByLabelText('Evidence run ID')
    view.rerender(<OperationsView {...props} sourceRunId="source-2" />)
    expect(screen.queryByLabelText('Evidence run ID')).not.toBeInTheDocument()
    await screen.findByRole('alert')
    view.rerender(<OperationsView {...props} />)
    await screen.findByText('Records received')
    expect(screen.getByLabelText('Evidence run ID')).toHaveValue('')
  })
  it('clears a valid source directly without retaining its draft fields', async () => {
    serve(overview(), call => call.path === '/api/runs/source-1' ? { status: 200, body: { id: 'source-1', goal: 'First source', state: 'completed', dataset_id: 'dataset-7' } } : undefined)
    const view = render(<OperationsView sourceRunId="source-1" onOpenRun={vi.fn()} />)
    expect(await screen.findByLabelText('Evidence run ID')).toHaveValue('source-1')
    fireEvent.change(screen.getByLabelText('Work title'), { target: { value: 'Unsaved first source work' } })
    view.rerender(<OperationsView onOpenRun={vi.fn()} />)
    await waitFor(() => expect(screen.getByLabelText('Evidence run ID')).toHaveValue(''))
    expect(screen.getByLabelText('Work title')).toHaveValue('')
    expect(screen.getByLabelText('Evidence run ID')).not.toHaveAttribute('readonly')
  })
  it('rejects a different returned run even when the dataset is valid', async () => {
    serve(overview(), call => call.path === '/api/runs/source-1' ? { status: 200, body: { id: 'source-2', goal: 'Wrong response', state: 'completed', dataset_id: 'dataset-7' } } : undefined)
    render(<OperationsView sourceRunId="source-1" onOpenRun={vi.fn()} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('could not be verified')
    expect(screen.queryByLabelText('Evidence run ID')).not.toBeInTheDocument()
  })
  it.each([null, undefined, ''])('rejects missing dataset identity %s instead of inferring it', async dataset_id => {
    serve(overview(), call => call.path === '/api/runs/source-1' ? { status: 200, body: { id: 'source-1', goal: 'RMD Asset_ID.csv', state: 'completed', dataset_id } } : undefined)
    render(<OperationsView sourceRunId="source-1" onOpenRun={vi.fn()} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('could not be verified')
    expect(screen.queryByLabelText('Evidence run ID')).not.toBeInTheDocument()
  })
  it.each([403, 404])('does not expose foreign or revoked source %s', async status => {
    serve(overview(), call => call.path === '/api/runs/foreign' ? { status, body: { detail: 'Not available' } } : undefined)
    render(<OperationsView sourceRunId="foreign" onOpenRun={vi.fn()} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Nothing was created')
    expect(screen.queryByText('Create work order draft')).not.toBeInTheDocument()
  })
  it('does not offer creation to an organization viewer even with a valid source', async () => {
    const data = overview(); data.permissions.write = false
    serve(data, call => call.path === '/api/runs/source-1' ? { status: 200, body: { id: 'source-1', goal: 'Selected source', state: 'completed', dataset_id: 'dataset-7' } } : undefined)
    render(<OperationsView sourceRunId="source-1" onOpenRun={vi.fn()} />)
    await screen.findByText('Records received')
    expect(screen.queryByText('Create work order draft')).not.toBeInTheDocument()
  })

  it('separates complete registry totals from the displayed work queue', async () => {
    const data = overview()
    data.assets.push({ ...asset, id: 'asset-2', name: 'Standby pump', external_id: 'P-20' })
    data.sites.push({ id: 'site-2', code: 'WS', name: 'West station' })
    data.work_orders = [workOrder(), { ...workOrder(), id: 'wo-2', status: 'authorized' }, { ...workOrder(), id: 'wo-3', status: 'completed' }]
    data.work_order_count = 88; data.work_orders_truncated = true
    serve(data)
    render(<OperationsView onOpenRun={vi.fn()} />)
    const coverage = await screen.findByLabelText('Registry coverage')
    expect(within(coverage).getByText('Registered assets').parentElement).toHaveTextContent('2')
    expect(within(coverage).getByText('Registered sites').parentElement).toHaveTextContent('2')
    expect(within(coverage).getByText('Recorded work orders').parentElement).toHaveTextContent('88')
    const summary = screen.getByRole('group', { name: 'Work order summary' })
    expect([...summary.querySelectorAll('.performance-value__number')].map((node) => node.textContent)).toEqual(['1', '1', '1'])
    expect(screen.getByText(/Showing 3 of 88 orders/)).toHaveTextContent('Workflow counts and filters cover this displayed queue')
  })

  it.each(['en', 'ar'] as const)('inspects only the selected asset with keyboard focus and truthful %s history', async (locale) => {
    applyLocale(locale, false)
    const data = overview(), openRun = vi.fn()
    data.assets.push({ ...asset, id: 'asset-2', name: 'Standby pump', external_id: 'P-20' })
    data.work_orders = [{ ...workOrder(), status: 'completed', completion: { outcome: 'Bearing wear confirmed', notes: 'Bearing replaced', labor_hours: 0, parts: [{ part: 'B-10', quantity: 2 }] },
      audit: [{ id: 'audit-1', action: 'work_completed', actor: 'maintenance-lead', created_at: '2026-10-21T10:00:00Z', version: 4, detail: {} }] },
    { ...workOrder(), id: 'wo-other', asset_id: 'asset-2', title: 'Unrelated work', evidence: { ...workOrder().evidence, source_asset_id: 'P-20', run_id: 'other-run' } }]
    data.work_order_count = 2
    const { calls } = serve(data)
    const user = userEvent.setup()
    render(<OperationsView onOpenRun={openRun} />)
    await user.click(await screen.findByRole('button', { name: locale === 'ar' ? 'استعراض سجل الأصول' : 'Browse asset registry' }))
    const trigger = screen.getByRole('button', { name: locale === 'ar' ? 'فحص الأصل: Cooling pump' : 'Inspect asset: Cooling pump' })
    trigger.focus(); await user.keyboard('{Enter}')
    const dialog = screen.getByRole('dialog', { name: locale === 'ar' ? 'تفاصيل الأصل' : 'Asset details' })
    expect(dialog).toHaveFocus()
    expect(document.documentElement.dir).toBe(locale === 'ar' ? 'rtl' : 'ltr')
    expect(dialog).toHaveTextContent(locale === 'ar' ? 'لا يحتوي السجل على قياس للحالة' : 'The registry contains no measured condition or health score')
    expect(within(dialog).queryByText('Unrelated work')).not.toBeInTheDocument()
    await user.click(within(dialog).getByText('Inspect pump bearing'))
    expect(within(dialog).getByText('Bearing wear confirmed')).toBeVisible()
    expect(within(dialog).getByText('maintenance-lead')).toBeVisible()
    expect(within(dialog).getByText('B-10')).toBeVisible()
    const laborLabel = within(dialog).getByText(locale === 'ar' ? 'ساعات العمل' : 'Labor hours')
    expect(laborLabel.nextElementSibling).toHaveTextContent('0')
    expect(within(dialog).getByText('run-1')).toBeVisible()
    expect(within(dialog).queryByText('other-run')).not.toBeInTheDocument()
    await user.keyboard('{Shift>}{Tab}{/Shift}')
    expect(within(dialog).getByRole('button', { name: locale === 'ar' ? 'إغلاق تفاصيل الأصل' : 'Close asset details' })).toHaveFocus()
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(trigger).toHaveFocus()
    await user.keyboard('{Enter}')
    const reopened = screen.getByRole('dialog')
    await user.click(within(reopened).getByText('Inspect pump bearing'))
    await user.click(within(reopened).getByRole('button', { name: locale === 'ar' ? 'فتح التحليل المرجعي' : 'Open source run' }))
    expect(openRun).toHaveBeenCalledExactlyOnceWith('run-1')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(calls.every((call) => call.method === 'GET')).toBe(true)
  })

  it('discloses a partial asset history even when no linked order is displayed', async () => {
    const data = overview()
    data.work_order_count = 203; data.work_orders_truncated = true
    serve(data)
    const user = userEvent.setup()
    render(<OperationsView onOpenRun={vi.fn()} />)
    await user.click(await screen.findByRole('button', { name: 'Browse asset registry' }))
    await user.click(screen.getByRole('button', { name: 'Inspect asset: Cooling pump' }))
    const dialog = screen.getByRole('dialog')
    expect(dialog).toHaveTextContent('Partial history: the organization queue contains 0 of 203 orders')
    expect(dialog).toHaveTextContent('No linked orders in this queue')
    expect(dialog).toHaveTextContent('This does not establish asset health')
  })

  it('searches registry identity and keeps unsaved forms through inspection and section changes', async () => {
    serve()
    const user = userEvent.setup()
    render(<OperationsView onOpenRun={vi.fn()} />)
    await user.click(await screen.findByRole('button', { name: 'Browse asset registry' }))
    expect(document.getElementById('operations-registry-panel')).toHaveFocus()
    fireEvent.change(screen.getByLabelText('Site name'), { target: { value: 'Unsaved site' } })
    await user.type(screen.getByLabelText('Search registered assets'), 'P-10')
    await user.click(screen.getByRole('button', { name: 'Inspect asset: Cooling pump' }))
    await user.keyboard('{Escape}')
    await user.click(screen.getByRole('button', { name: 'Work orders' }))
    await user.click(screen.getByRole('button', { name: 'Sites and assets' }))
    expect(screen.getByLabelText('Site name')).toHaveValue('Unsaved site')
    expect(screen.getByLabelText('Search registered assets')).toHaveValue('P-10')
    fireEvent.change(screen.getByLabelText('Search registered assets'), { target: { value: 'not-registered' } })
    expect(screen.getByRole('heading', { name: 'No matching assets' })).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Inspect asset: Cooling pump' })).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Clear asset search' }))
    expect(screen.getByRole('button', { name: 'Inspect asset: Cooling pump' })).toBeVisible()
  })

  it('shows setup guidance without fabricated totals before an organization exists', async () => {
    serve(overview(), (call) => call.path === '/api/operations/organizations' ? { status: 200, body: { organizations: [] } } : undefined)
    render(<OperationsView onOpenRun={vi.fn()} />)
    expect(await screen.findByRole('heading', { name: 'Create a workspace for your maintenance team.' })).toBeVisible()
    expect(screen.getByLabelText('Organization name')).toBeVisible()
    expect(screen.getByText('Authorize work explicitly, then record what happened.')).toBeVisible()
    expect(screen.queryByLabelText('Registry coverage')).not.toBeInTheDocument()
  })

  it.each(['en', 'ar'] as const)('keeps zero counts and completed work neutral with visible %s assessment labels', async (locale) => {
    applyLocale(locale, false)
    const data = overview()
    data.work_orders = [{ ...workOrder(), status: 'completed' }]
    data.work_order_count = 1
    serve(data)
    render(<OperationsView onOpenRun={vi.fn()} />)
    const summary = await screen.findByRole('group', { name: locale === 'ar' ? 'ملخص أوامر العمل' : 'Work order summary' })
    expect(within(summary).getAllByText(locale === 'ar' ? 'غير مقيّم' : 'Not assessed')).toHaveLength(3)
    expect(summary.querySelectorAll('[data-performance="unassessed"]')).toHaveLength(3)
    expect(summary.querySelector('[data-performance="good"]')).toBeNull()
    expect([...summary.querySelectorAll('.performance-value__number')].map((node) => node.textContent)).toEqual(['0', '0', '1'])
  })

  it('records an evidence-linked draft, explicit authorization and observed repair outcome', async () => {
    const { calls, state } = serve()
    const user = userEvent.setup(), openRun = vi.fn()
    render(<OperationsView onOpenRun={openRun} />)
    await openDraft(user)
    await user.click(screen.getByRole('button', { name: 'Save draft' }))
    const detail = await screen.findByRole('region', { name: 'Work order details' })
    expect(state.work_orders[0].status).toBe('draft')
    expect(calls.find((call) => call.path.endsWith('/work-orders'))?.body).toMatchObject({ run_id: 'run-1', asset_column: 'Asset_ID', source_asset_id: 'P-10' })
    await user.click(within(detail).getByText('Source evidence'))
    await user.click(within(detail).getByRole('button', { name: 'Open source run' }))
    expect(openRun).toHaveBeenCalledWith('run-1')
    await user.click(within(detail).getByRole('button', { name: 'Authorize maintenance' }))
    expect(calls.filter((call) => call.method === 'PATCH')).toHaveLength(0)
    const dialog = screen.getByRole('dialog')
    expect(dialog).toHaveTextContent('Report publication approval is a separate decision')
    await user.click(within(dialog).getByRole('button', { name: 'Authorize maintenance' }))
    await user.click(await screen.findByRole('button', { name: 'Start work' }))
    await user.type(await screen.findByLabelText('Observed outcome'), 'Bearing wear confirmed')
    await user.type(screen.getByLabelText('Work performed and findings'), 'Replaced bearing and checked vibration')
    fireEvent.change(screen.getByLabelText('Labor hours'), { target: { value: '2.5' } })
    await user.click(screen.getByRole('button', { name: 'Add part' }))
    await user.type(screen.getByLabelText('Part name or code 1'), 'Bearing B-10')
    await user.click(screen.getByRole('button', { name: 'Record completion' }))
    await waitFor(() => expect(state.work_orders[0].status).toBe('completed'))
    expect(state.work_orders[0].completion).toEqual({ outcome: 'Bearing wear confirmed', notes: 'Replaced bearing and checked vibration', labor_hours: 2.5, parts: [{ part: 'Bearing B-10', quantity: 1 }] })
    expect(calls.filter((call) => call.method === 'PATCH').map((call) => call.body.expected_version)).toEqual([1, 2, 3])
    expect(localStorage.getItem('operations-draft')).toBeNull()
    // This journey types several fields and verifies three governed state
    // transitions; allow its work to finish on the Windows test host.
  }, 10_000)

  it('keeps input and reuses the same operation key after an uncertain network response', async () => {
    let offline = true
    const { calls } = serve(overview(), (call) => call.method === 'POST' && call.path.endsWith('/work-orders') && offline ? 'offline' : undefined)
    const user = userEvent.setup()
    render(<OperationsView onOpenRun={vi.fn()} />)
    await openDraft(user)
    await user.click(screen.getByRole('button', { name: 'Save draft' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Your entries are still here')
    expect(screen.getByLabelText('Work title')).toHaveValue('Inspect pump bearing')
    expect(calls.filter((call) => call.method === 'POST')).toHaveLength(1)
    offline = false
    await user.click(screen.getAllByRole('button', { name: 'Refresh' }).at(-1)!)
    await screen.findByText('Records received')
    await user.click(screen.getByRole('button', { name: 'Save draft' }))
    await screen.findByRole('region', { name: 'Work order details' })
    const attempts = calls.filter((call) => call.method === 'POST')
    expect(attempts).toHaveLength(2)
    expect(attempts[0].body.idempotency_key).toBe(attempts[1].body.idempotency_key)
  })

  it('requires a refresh and a new explicit submit after a version conflict', async () => {
    const data = overview(); data.work_orders = [workOrder()]
    let conflict = true
    const { calls } = serve(data, (call) => {
      if (conflict && call.method === 'PATCH') { data.work_orders[0].version = 2; return { status: 409 } }
      return undefined
    })
    const user = userEvent.setup()
    render(<OperationsView onOpenRun={vi.fn()} />)
    await user.click(await screen.findByRole('button', { name: /Inspect pump bearing/ }))
    const detail = screen.getByRole('region', { name: 'Work order details' })
    await user.selectOptions(within(detail).getByLabelText('Priority'), 'critical')
    await user.click(within(detail).getByRole('button', { name: 'Save assignment and priority' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Another change was recorded first')
    await user.click(screen.getByRole('button', { name: 'Refresh' }))
    await screen.findByText('Version 2')
    expect(calls.filter((call) => call.method === 'PATCH')).toHaveLength(1)
    expect(within(detail).getByLabelText('Priority')).toHaveValue('critical')
    conflict = false
    await user.click(within(detail).getByRole('button', { name: 'Save assignment and priority' }))
    await waitFor(() => expect(calls.filter((call) => call.method === 'PATCH')).toHaveLength(2))
    expect(calls.filter((call) => call.method === 'PATCH')[1].body.expected_version).toBe(2)
  })

  it('uses Arabic controls, RTL and Arabic server errors for the authorization journey', async () => {
    act(() => applyLocale('ar', false))
    const data = overview(); data.work_orders = [workOrder()]
    const { calls } = serve(data)
    const user = userEvent.setup()
    render(<OperationsView onOpenRun={vi.fn()} />)
    await user.click(await screen.findByRole('button', { name: /Inspect pump bearing/ }))
    expect(document.documentElement.dir).toBe('rtl')
    await user.click(screen.getByRole('button', { name: 'التصريح بتنفيذ الصيانة' }))
    const dialog = screen.getByRole('dialog')
    expect(dialog).toHaveTextContent('الموافقة على نشر التقرير قرار مستقل')
    await user.click(within(dialog).getByRole('button', { name: 'التصريح بتنفيذ الصيانة' }))
    await screen.findByRole('button', { name: 'بدء العمل' })
    expect(calls.filter((call) => call.path.startsWith('/api/operations')).every((call) => call.language === 'ar')).toBe(true)
  })

  it('restricts technician controls to assigned work and hides membership administration', async () => {
    const data = overview(); data.organization.role = 'technician'; data.principal_subject = 'technician-2'
    data.permissions = { read: true, write: true, manage: false, authorize: false }
    data.work_orders = [{ ...workOrder(), status: 'authorized' }]
    serve(data)
    const user = userEvent.setup()
    render(<OperationsView onOpenRun={vi.fn()} />)
    await user.click(await screen.findByRole('button', { name: /Inspect pump bearing/ }))
    expect(screen.queryByRole('button', { name: 'Start work' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Save assignment and priority' })).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Team access' }))
    expect(screen.queryByRole('button', { name: 'Save membership' })).not.toBeInTheDocument()
  })

  it('registers a real site and asset before an explicit JSON batch import', async () => {
    const data = overview(); data.sites = []; data.assets = []
    const { calls } = serve(data)
    const user = userEvent.setup()
    render(<OperationsView onOpenRun={vi.fn()} />)
    await user.click(await screen.findByRole('button', { name: 'Sites and assets' }))
    await user.type(screen.getByLabelText('Site name'), 'Cooling plant')
    await user.type(screen.getByLabelText('Site code'), 'CP')
    await user.click(screen.getByRole('button', { name: 'Add site' }))
    await waitFor(() => expect(screen.getByLabelText('Site')).toBeEnabled())
    await user.selectOptions(screen.getByLabelText('Site'), site.id)
    await user.type(screen.getByLabelText('Asset name'), 'Cooling pump')
    await user.type(screen.getByLabelText('External asset ID'), 'P-10')
    await user.type(screen.getByLabelText('Source system'), 'CMMS')
    await user.click(screen.getByRole('button', { name: 'Register asset' }))
    await waitFor(() => expect(data.assets).toHaveLength(1))
    await user.click(screen.getByText('Import registered assets'))
    const file = new File(['invalid'], 'assets.json', { type: 'application/json' })
    Object.defineProperty(file, 'text', { value: async () => JSON.stringify({ schema_version: 1, assets: [{ site_id: site.id, external_id: 'P-20', source_system: 'CMMS', name: 'Standby pump', criticality: 'high' }] }) })
    await user.upload(screen.getByLabelText('Asset JSON file'), file)
    await screen.findByText('1 asset records ready for server validation.')
    expect(calls.filter((call) => call.path.endsWith('/import/assets'))).toHaveLength(0)
    await user.click(screen.getByRole('button', { name: 'Import assets' }))
    await waitFor(() => expect(calls.filter((call) => call.path.endsWith('/import/assets'))).toHaveLength(1))
  })

  it('requires a separate confirmation before removing organization access', async () => {
    const { calls } = serve()
    const user = userEvent.setup()
    render(<OperationsView onOpenRun={vi.fn()} />)
    await user.click(await screen.findByRole('button', { name: 'Team access' }))
    await user.type(screen.getByLabelText('Managed identity subject'), 'technician-2')
    await user.selectOptions(screen.getByLabelText('Organization role'), 'removed')
    await user.click(screen.getByRole('button', { name: 'Save membership' }))
    const dialog = screen.getByRole('dialog')
    expect(dialog).toHaveTextContent('technician-2')
    expect(calls.filter((call) => call.path.endsWith('/members'))).toHaveLength(0)
    await user.click(within(dialog).getByRole('button', { name: 'Remove access' }))
    await waitFor(() => expect(calls.filter((call) => call.path.endsWith('/members'))).toHaveLength(1))
    expect(calls.find((call) => call.path.endsWith('/members'))?.body).toMatchObject({ subject: 'technician-2', role: 'removed', expected_version: 1 })
  })
})

describe('prospective validation interface', () => {
  const fraction = { numerator: 0, denominator: 0, value: null, wilson_95: null }
  function fixture() {
    return { id: 'trial-1', revision: 1, protocol: { name: 'Pump pilot', model_version: 'model-1', baseline_name: 'base-1', trained_through: '2026-01-01T00:00:00Z', registered_at: '2026-10-01T00:00:00Z', horizon_hours: 24, threshold: 0.7, failure_definition: 'Confirmed bearing failure', cohort_definition: 'Registered pumps' }, predictions: [] as Array<Record<string, unknown>>, metrics: { registered: 0, evaluated: 0, pending: 0, failure_alert_precision: fraction, failure_window_recall: fraction, actionable_alert_precision: fraction, brier_score: null, baseline: { brier_score: null }, lead_time_hours: { mean: null }, false_alerts_per_asset_month: null, calibration: [] } }
  }
  it('registers a protocol and future prediction without inventing measurable results', async () => {
    const trial = fixture(), calls: Call[] = []
    let created = false
    vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
      const path = new URL(url, 'http://localhost').pathname
      const body = init?.body ? JSON.parse(String(init.body)) : {}
      calls.push({ path, method: init?.method ?? 'GET', body, language: 'en' })
      if (init?.method === 'POST') {
        if (path.endsWith('/predictions')) { trial.revision++; trial.predictions.push({ ...body, id: 'prediction-1', predicted_at: '2026-10-21T12:00:00Z', window_end: '2026-10-22T12:00:00Z', outcome: null }); trial.metrics.registered++; trial.metrics.pending++ }
        else { created = true; trial.protocol = { ...trial.protocol, ...body } }
      }
      return { ok: true, status: 200, json: async () => structuredClone(path.endsWith('/organizations/org-1/trials') && init?.method !== 'POST' ? { trials: created ? [trial] : [] } : trial) } as Response
    }))
    const user = userEvent.setup()
    render(<ValidationPanel data={overview()} />)
    await screen.findByText('No validation protocol registered.')
    await user.click(screen.getByText('Register protocol', { selector: 'summary' }))
    await user.type(screen.getByLabelText('Trial name'), 'Pump pilot')
    await user.type(screen.getByLabelText('Model version'), 'model-1')
    await user.type(screen.getByLabelText('Baseline name'), 'base-1')
    fireEvent.change(screen.getByLabelText('Training data ends at (local time)'), { target: { value: '2026-01-01T00:00' } })
    await user.type(screen.getByLabelText('Observation window (hours)'), '24')
    await user.type(screen.getByLabelText('Alert threshold (0–1)'), '0.7')
    await user.type(screen.getByLabelText('What counts as a failure?'), 'Confirmed bearing failure')
    await user.type(screen.getByLabelText('Eligible asset population'), 'Registered pumps')
    await user.click(screen.getByRole('button', { name: 'Register protocol' }))
    const metrics = (await screen.findByRole('heading', { name: 'Observed validation results' })).closest('section')!
    expect(screen.getAllByText('Not yet measurable').length).toBeGreaterThan(0)
    expect(within(metrics).getAllByText('Unavailable')).toHaveLength(7)
    expect(within(metrics).getAllByText('Not assessed')).toHaveLength(3)
    await user.click(screen.getByText('Register prediction', { selector: 'summary' }))
    await user.selectOptions(screen.getByLabelText('Registered asset'), asset.id)
    await user.type(screen.getByLabelText('Model failure probability (0–1)'), '0.8')
    await user.type(screen.getByLabelText('Baseline failure probability (0–1)'), '0.3')
    await user.click(screen.getByRole('button', { name: 'Register prediction' }))
    await waitFor(() => expect(trial.predictions).toHaveLength(1))
    const posts = calls.filter((call) => call.method === 'POST')
    expect(posts[0].body.request_id).toEqual(expect.any(String))
    expect(posts[1].body).toMatchObject({ revision: 1, asset_id: asset.id, probability: 0.8, baseline_probability: 0.3, request_id: expect.any(String) })
    expect(posts[1].body).not.toHaveProperty('predicted_at')
    expect(posts[1].body).not.toHaveProperty('outcome')
  })

  it('keeps an adjudication explicitly confirmed and preserves evidence on a server refusal', async () => {
    const trial = fixture()
    trial.predictions.push({ id: 'prediction-1', asset_id: asset.id, probability: 0.8, baseline_probability: 0.3, predicted_at: '2026-10-21T12:00:00Z', window_end: '2026-10-22T12:00:00Z', outcome: null })
    const posts: unknown[] = []
    vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
      const isPost = init?.method === 'POST'
      if (isPost) posts.push(JSON.parse(String(init.body)))
      const body = isPost ? { detail: { message: 'Wait until the full prediction window has ended.' } } : new URL(url, 'http://localhost').pathname.endsWith('/organizations/org-1/trials') ? { trials: [trial] } : trial
      return { ok: !isPost, status: isPost ? 409 : 200, json: async () => body } as Response
    }))
    const user = userEvent.setup()
    render(<ValidationPanel data={overview()} />)
    await screen.findByRole('heading', { name: 'Observed validation results' })
    await user.click(screen.getByText('Record observed outcome', { selector: 'summary' }))
    await user.selectOptions(screen.getByLabelText('Prediction window'), 'prediction-1')
    await user.selectOptions(screen.getByLabelText('Did the defined failure occur?'), 'no')
    fireEvent.change(screen.getByLabelText('Observed through (local time)'), { target: { value: '2026-10-22T12:00' } })
    await user.type(screen.getByLabelText('Evidence reference'), 'Inspection log 20')
    expect(screen.getByRole('button', { name: 'Record observed outcome' })).toBeDisabled()
    await user.click(screen.getByRole('checkbox'))
    await user.click(screen.getByRole('button', { name: 'Record observed outcome' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Wait until the full prediction window has ended')
    expect(screen.getByLabelText('Evidence reference')).toHaveValue('Inspection log 20')
    expect(posts).toHaveLength(1)
    expect(posts[0]).toMatchObject({ failed: false, actionable: null, failure_at: null, evidence_reference: 'Inspection log 20', revision: 1 })
  })
})
