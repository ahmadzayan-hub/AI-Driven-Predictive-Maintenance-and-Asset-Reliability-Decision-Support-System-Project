import { useCallback, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { usePack } from '../../i18n/pack'
import { Dialog } from '../../shared/components/Dialog'
import { Icon } from '../../shared/components/Icon'
import { AssetInspector } from './AssetInspector'
import { messages } from './messages'
import { Field } from './OperationsView'
import type { Mutate } from './OperationsView'
import { operationsApi } from './operationsApi'
import type { Asset, OperationsOverview, OperationsRole, Priority } from './types'

export const priorities: Priority[] = ['critical', 'high', 'medium', 'low']
interface Props { data: OperationsOverview; busy: boolean; mutate: Mutate }

export function RegistryPanel({ data, busy, mutate, onOpenRun }: Props & { onOpenRun: (id: string) => void }) {
  const { t } = usePack(messages)
  const [query, setQuery] = useState(''), [inspected, setInspected] = useState<string | null>(null)
  const closeInspector = useCallback(() => setInspected(null), [])
  const selectedAsset = data.assets.find((asset) => asset.id === inspected)
  const search = query.trim().toLocaleLowerCase()
  const matchingAssets = data.assets.filter((asset) => [asset.name, asset.external_id, asset.source_system, data.sites.find((site) => site.id === asset.site_id)?.name ?? ''].some((value) => value.toLocaleLowerCase().includes(search)))
  const [siteName, setSiteName] = useState(''), [siteCode, setSiteCode] = useState('')
  const [siteId, setSiteId] = useState(''), [name, setName] = useState(''), [externalId, setExternalId] = useState('')
  const [source, setSource] = useState(''), [criticality, setCriticality] = useState<Priority>('medium')
  const organization = data.organization.id
  async function createSite(event: FormEvent) {
    event.preventDefault()
    const body = { name: siteName.trim(), code: siteCode.trim() }
    if (await mutate('site', body, (key) => operationsApi.createSite(organization, body, key))) { setSiteName(''); setSiteCode('') }
  }
  async function createAsset(event: FormEvent) {
    event.preventDefault()
    const body = { site_id: siteId, name: name.trim(), external_id: externalId.trim(), source_system: source.trim(), criticality }
    if (await mutate('asset', body, (key) => operationsApi.createAsset(organization, body, key))) { setName(''); setExternalId('') }
  }
  return <section aria-label={t('registry')}>
    <div className="operations__section-heading"><div><h3>{t('assetRegister')}</h3><p className="operations__muted">{t('registryHelp')}</p></div><span className="operations__count">{t('assetCount', { n: data.assets.length })}</span></div>
    {data.assets.length > 0 && <Field label={t('searchAssets')}><input type="search" value={query} onChange={(event) => setQuery(event.target.value)} /></Field>}
    <div className="operations__registry-list">
      {data.sites.filter((site) => !search || matchingAssets.some((asset) => asset.site_id === site.id)).map((site) => <section className="operations__card" key={site.id}>
        <h3 dir="auto">{site.name} <small className="operations__code">{site.code}</small></h3>
        <p>{t('siteIdentifier')}: <bdi className="operations__code">{site.id}</bdi></p>
        <ul className="operations__asset-list">{matchingAssets.filter((asset) => asset.site_id === site.id).map((asset) => <li key={asset.id}>
          <button type="button" className="operations__asset-button" aria-label={t('inspectAsset', { name: asset.name })} aria-haspopup="dialog" onClick={() => setInspected(asset.id)}>
            <span className="operations__asset-identity"><Icon name="settings" size={20} /><span><strong dir="auto">{asset.name}</strong><span className="operations__muted" dir="auto">{asset.source_system} · {asset.external_id}</span></span></span>
            <span className="operations__asset-labels"><span>{t('criticality')}: {t(asset.criticality)}</span><span className="operations__muted">{t('assetQueueCount', { n: data.work_orders.filter((order) => order.asset_id === asset.id).length })}</span></span>
          </button>
        </li>)}</ul>
        {!data.assets.some((asset) => asset.site_id === site.id) && <p className="operations__muted">{t('siteEmpty')}</p>}
      </section>)}
      {!data.assets.length && <div className="operations__empty"><Icon name="database" size={28} /><h3>{t('noAssets')}</h3><p>{t(data.permissions.manage ? 'registryEmptyHelp' : 'manageOnly')}</p></div>}
      {data.assets.length > 0 && !matchingAssets.length && <div className="operations__empty operations__empty--compact"><Icon name="search" size={24} /><h3>{t('noAssetMatches')}</h3><p>{t('assetSearchHelp')}</p><button type="button" className="btn btn--ghost" onClick={() => setQuery('')}>{t('clearSearch')}</button></div>}
    </div>
    {data.permissions.manage ? <div className="operations__forms">
      <form className="operations__card" onSubmit={(event) => void createSite(event)}>
        <h3>{t('addSite')}</h3><fieldset disabled={busy}>
          <Field label={t('siteName')}><input required maxLength={120} value={siteName} onChange={(event) => setSiteName(event.target.value)} /></Field>
          <Field label={t('siteCode')}><input required maxLength={60} value={siteCode} onChange={(event) => setSiteCode(event.target.value)} dir="auto" /></Field>
          <button className="btn btn--primary">{t('addSite')}</button>
        </fieldset>
      </form>
      <form className="operations__card" onSubmit={(event) => void createAsset(event)}>
        <h3>{t('addAsset')}</h3>{!data.sites.length && <p>{t('noSites')}</p>}<fieldset disabled={busy || !data.sites.length}>
          <Field label={t('site')}><select required value={siteId} onChange={(event) => setSiteId(event.target.value)}><option value="">{t('choose')}</option>{data.sites.map((site) => <option value={site.id} key={site.id}>{site.name}</option>)}</select></Field>
          <Field label={t('assetName')}><input required maxLength={160} value={name} onChange={(event) => setName(event.target.value)} /></Field>
          <Field label={t('assetId')}><input required maxLength={160} dir="auto" value={externalId} onChange={(event) => setExternalId(event.target.value)} /></Field>
          <Field label={t('sourceSystem')}><input required maxLength={80} value={source} onChange={(event) => setSource(event.target.value)} /></Field>
          <Field label={t('criticality')}><select value={criticality} onChange={(event) => setCriticality(event.target.value as Priority)}>{priorities.map((priority) => <option key={priority} value={priority}>{t(priority)}</option>)}</select></Field>
          <button className="btn btn--primary">{t('addAsset')}</button>
        </fieldset>
      </form>
    </div> : <p>{t('manageOnly')}</p>}
    {data.permissions.manage && <AssetImport data={data} busy={busy} mutate={mutate} />}
    {selectedAsset && <AssetInspector asset={selectedAsset} data={data} onClose={closeInspector} onOpenRun={onOpenRun} />}
  </section>
}

function AssetImport({ data, busy, mutate }: Props) {
  const { t } = usePack(messages)
  const [assets, setAssets] = useState<Omit<Asset, 'id'>[] | null>(null)
  const [invalid, setInvalid] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)
  const sequence = useRef(0)
  async function read(file?: File) {
    const attempt = ++sequence.current
    setAssets(null); setInvalid(false)
    if (!file) return
    try {
      if (file.size > 1_000_000) throw new Error('size')
      const body: unknown = JSON.parse(await file.text())
      if (attempt !== sequence.current) return
      if (!body || typeof body !== 'object' || !('schema_version' in body) || body.schema_version !== 1 || !('assets' in body) || !Array.isArray(body.assets) || !body.assets.length || body.assets.length > 500) throw new Error('shape')
      const fields = ['site_id', 'external_id', 'source_system', 'name', 'criticality'] as const
      if (!body.assets.every((item: unknown) => item && typeof item === 'object' && fields.every((field) => field in item && typeof (item as Record<string, unknown>)[field] === 'string') && Object.keys(item).every((field) => (fields as readonly string[]).includes(field)))) throw new Error('fields')
      setAssets(body.assets as Omit<Asset, 'id'>[])
    } catch { if (attempt === sequence.current) setInvalid(true) }
  }
  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!assets) return
    if (await mutate('asset-import', { assets }, (key) => operationsApi.importAssets(data.organization.id, assets, key))) {
      setAssets(null)
      if (fileInput.current) fileInput.current.value = ''
    }
  }
  return <details className="operations__card"><summary>{t('importTitle')}</summary><form onSubmit={(event) => void submit(event)}><fieldset disabled={busy}>
    <p id="operations-import-help">{t('importHelp')}</p>
    <Field label={t('importFile')}><input ref={fileInput} type="file" accept=".json,application/json" aria-describedby="operations-import-help" onChange={(event) => void read(event.target.files?.[0])} /></Field>
    {invalid && <p role="alert">{t('importInvalid')}</p>}
    {assets && <><p role="status">{t('importPreview', { n: assets.length })}</p><ul>{assets.slice(0, 5).map((asset, index) => <li dir="auto" key={index}>{asset.name} · {asset.external_id}</li>)}</ul></>}
    <button className="btn btn--primary" disabled={!assets}>{t('importSubmit')}</button>
  </fieldset></form></details>
}

export function TeamPanel({ data, busy, mutate }: Props) {
  const { t } = usePack(messages)
  const [subject, setSubject] = useState(''), [role, setRole] = useState<OperationsRole | 'removed'>('viewer'), [confirm, setConfirm] = useState(false)
  async function save(event: FormEvent) {
    event.preventDefault()
    if (role === 'removed') { setConfirm(true); return }
    await apply()
  }
  async function apply() {
    const body = { subject: subject.trim(), role, expected_version: data.organization.version }
    if (await mutate('member', body, (key) => operationsApi.saveMember(data.organization.id, body.subject, role, body.expected_version, key))) { setSubject(''); setConfirm(false) }
  }
  return <section className="operations__card" aria-label={t('team')}>
    <h3>{t('team')}</h3>
    <ul className="operations__assets">{data.members.map((member) => <li key={member.subject}><span className="operations__code" dir="auto">{member.subject}</span><span>{t(member.role)}</span></li>)}</ul>
    {data.permissions.manage && <form onSubmit={(event) => void save(event)}><fieldset disabled={busy}>
      <p id="operations-member-help">{t('memberHelp')}</p>
      <Field label={t('member')}><input required maxLength={200} value={subject} onChange={(event) => setSubject(event.target.value)} aria-describedby="operations-member-help" dir="auto" /></Field>
      <Field label={t('role')}><select value={role} onChange={(event) => setRole(event.target.value as OperationsRole | 'removed')}>{(['owner', 'manager', 'technician', 'viewer', 'removed'] as const).map((item) => <option key={item} value={item}>{t(item)}</option>)}</select></Field>
      <button className="btn btn--primary">{t('saveMember')}</button>
    </fieldset></form>}
    {confirm && <Dialog title={t('removeTitle')} labelledById="operations-remove-title" onClose={() => { if (!busy) setConfirm(false) }}><p className="dialog__body">{t('removeHelp')}</p><p className="dialog__body" dir="auto">{subject}</p><div className="dialog__actions"><button className="btn btn--ghost" disabled={busy} onClick={() => setConfirm(false)}>{t('cancel')}</button><button className="btn btn--danger" disabled={busy} onClick={() => void apply()}>{t('removed')}</button></div></Dialog>}
  </section>
}
