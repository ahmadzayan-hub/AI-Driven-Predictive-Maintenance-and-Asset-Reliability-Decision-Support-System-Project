import { request as transport } from '../../shared/api'
import { currentLocale } from '../../i18n'
import type { Asset, DraftOrder, Member, OperationsOverview, OperationsRole, OrderChange, Organization, Readiness, Site, WorkOrder } from './types'

const base = '/api/operations/organizations'
export const operationsRequest = <T>(url: string, init?: RequestInit) => transport<T>(`${url}?language=${currentLocale()}`, init)
const request = operationsRequest
const path = (organization: string) => `${base}/${encodeURIComponent(organization)}`
const post = <T>(url: string, body: object, key: string) => request<T>(url, {
  method: 'POST', body: JSON.stringify({ ...body, idempotency_key: key }),
})

export const operationsApi = {
  organizations: () => request<{ organizations: Organization[] }>(base),
  createOrganization: (name: string, key: string) => post<Organization>(base, { name }, key),
  overview: (organization: string) => request<OperationsOverview>(`${path(organization)}/overview`),
  readiness: (organization: string) => request<Readiness>(`${path(organization)}/readiness`),
  createSite: (organization: string, data: Pick<Site, 'name' | 'code'>, key: string) => post<Site>(`${path(organization)}/sites`, data, key),
  createAsset: (organization: string, data: Omit<Asset, 'id'>, key: string) => post<Asset>(`${path(organization)}/assets`, data, key),
  importAssets: (organization: string, assets: Omit<Asset, 'id'>[], key: string) => post<unknown>(`${path(organization)}/import/assets`, { schema_version: 1, assets }, key),
  saveMember: (organization: string, subject: string, role: OperationsRole | 'removed', expected_version: number, key: string) => post<Member>(`${path(organization)}/members`, { subject, role, expected_version }, key),
  createOrder: (organization: string, data: DraftOrder, key: string) => post<WorkOrder>(`${path(organization)}/work-orders`, data, key),
  updateOrder: (organization: string, order: string, data: OrderChange, key: string) => request<WorkOrder>(`${path(organization)}/work-orders/${encodeURIComponent(order)}`, {
    method: 'PATCH', body: JSON.stringify({ ...data, idempotency_key: key }),
  }),
  export: (organization: string) => request<Record<string, unknown>>(`${path(organization)}/export`),
}

/** Keep the same key for a manually retried, identical request after an
 * uncertain response. Changed data is a distinct operation. Never auto-replay. */
export function requestKey() {
  let signature = '', key = ''
  return (body: unknown) => {
    const next = JSON.stringify(body)
    if (signature !== next || !key) { signature = next; key = crypto.randomUUID() }
    return key
  }
}
