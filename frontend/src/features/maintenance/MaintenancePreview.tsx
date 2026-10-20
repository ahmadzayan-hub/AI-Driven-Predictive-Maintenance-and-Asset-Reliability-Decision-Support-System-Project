import { useCallback, useEffect, useRef, useState } from 'react'
import { applyLocale } from '../../i18n'
import { usePack } from '../../i18n/pack'
import { useTheme } from '../../app/useTheme'
import { Icon } from '../../shared/components/Icon'
import type { IconName } from '../../shared/components/Icon'
import { Dialog } from '../../shared/components/Dialog'
import { PerformanceValue } from '../../shared/components/PerformanceValue'
import { maintenanceMessages } from './messages'
import { SAMPLE_ASSETS, SITES, assetCost, assetDowntime, severity, summarize } from './sample'
import type { Period, SampleAsset, Site } from './sample'
import './maintenance.css'

const PAGES = ['overview', 'reliability', 'work', 'cost', 'models'] as const
type Page = typeof PAGES[number]
const PAGE_ICONS: Record<Page, IconName> = { overview: 'dashboard', reliability: 'activity', work: 'check', cost: 'database', models: 'sparkle' }
const CONDITIONS = ['healthy', 'watch', 'critical'] as const
const CONDITION_TONE = { healthy: 'good', watch: 'okay', critical: 'bad' } as const

export function MaintenancePreview() {
  const { t, locale } = usePack(maintenanceMessages)
  const { isDark, toggleTheme } = useTheme()
  const [page, setPage] = useState<Page>('overview')
  const [site, setSite] = useState<Site | 'all'>('all')
  const [period, setPeriod] = useState<Period>('current')
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<SampleAsset | null>(null)
  const [reviewed, setReviewed] = useState<Set<string>>(() => new Set())
  const [notice, setNotice] = useState('')
  const heading = useRef<HTMLHeadingElement>(null)
  const previousPage = useRef(page)
  const wasEvidenceOpen = useRef(false)
  const closeEvidence = useCallback(() => setSelected(null), [])
  useEffect(() => {
    // A reviewed row leaves the queue. If its opener no longer exists, return
    // keyboard focus to the view heading after the dialog restores focus.
    if (wasEvidenceOpen.current && !selected && document.activeElement === document.body) heading.current?.focus()
    wasEvidenceOpen.current = selected !== null
  }, [selected])
  useEffect(() => {
    if (previousPage.current !== page) heading.current?.focus()
    previousPage.current = page
  }, [page])

  const number = (value: number, digits = 0) => new Intl.NumberFormat(locale === 'ar' ? 'ar-u-nu-latn' : 'en-US', { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(value)
  const money = (value: number) => `${number(value)} ${t('maint.usd')}`
  const month = (value: string) => new Intl.DateTimeFormat(locale === 'ar' ? 'ar' : 'en', { month: 'short', timeZone: 'UTC' }).format(new Date(`${value}-01T00:00:00Z`))
  const assets = SAMPLE_ASSETS.filter((asset) => (site === 'all' || asset.site === site) && `${asset.id} ${t(`maint.${asset.kind}`)}`.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase()))
  const summary = summarize(assets, period)
  const prioritized = [...assets].sort((a, b) => a.health - b.health)
  const queue = prioritized.filter((asset) => severity(asset) !== 'healthy' && !reviewed.has(asset.id))
  const tableAssets = page === 'overview' ? prioritized.slice(0, 4) : page === 'work' ? queue : prioritized
  const leading = [...assets].sort((a, b) => assetDowntime(b, period) - assetDowntime(a, period))[0]
  const maxTrend = Math.max(10, Math.ceil(Math.max(...summary.series.map((point) => point.value)) / 10) * 10)
  const points = summary.series.map((point, index) => `${48 + index * 500 / Math.max(1, summary.series.length - 1)},${176 - point.value / maxTrend * 138}`)

  function reset() { setSite('all'); setPeriod('current'); setSearch('') }
  function download() {
    const rows = [
      ['source', 'site', 'period', 'equipment', 'availability_pct', 'downtime_hours', 'maintenance_cost_usd'],
      ['fictional-ui-design-fixture', site, period, String(summary.count), summary.availability?.toFixed(2) ?? '', String(summary.downtime), String(summary.cost)],
    ]
    const url = URL.createObjectURL(new Blob([rows.map((row) => row.join(',')).join('\r\n')], { type: 'text/csv;charset=utf-8' }))
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'synthetic-maintenance-preview-summary.csv'
    anchor.click()
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    setNotice(t('maint.exported'))
  }

  const statusBadge = (asset: SampleAsset) => <span className={`maintenance__badge maintenance__badge--${severity(asset)}`}><span aria-hidden="true" />{t(`maint.${severity(asset)}`)}</span>
  const healthValue = (asset: SampleAsset) => <PerformanceValue tone={CONDITION_TONE[severity(asset)]} status={t(`maint.${severity(asset)}`)}><bdi dir="ltr">{number(asset.health)}<small>/100</small></bdi></PerformanceValue>

  const equipmentTable = (
    <section className="maintenance__panel maintenance__equipment" aria-labelledby="equipment-title">
      <div className="maintenance__panel-head">
        <div><h2 id="equipment-title">{t(page === 'reliability' ? 'maint.equipment' : 'maint.queue')}</h2><p>{t('maint.queueSub')}</p></div>
        {page === 'overview' && <button className="maintenance__text-button" onClick={() => setPage('reliability')}>{t('maint.viewAll')} <span aria-hidden="true">↗</span></button>}
      </div>
      {tableAssets.length ? <div className="maintenance__table-scroll" role="region" aria-label={t('maint.equipment')} tabIndex={0}>
        <table><thead><tr><th>{t('maint.equipment')}</th><th>{t('maint.health')}</th><th>{t('maint.status')}</th><th>{t('maint.action')}</th></tr></thead>
          <tbody>{tableAssets.map((asset) => <tr key={asset.id}>
            <td><bdi className="maintenance__equipment-id">{asset.id}</bdi><span className="maintenance__table-detail">{t(`maint.${asset.kind}`)} · {t(`maint.${asset.site}`)}</span></td>
            <td><div className="maintenance__health">{healthValue(asset)}<div aria-hidden="true"><i className={`maintenance__health--${severity(asset)}`} style={{ width: `${asset.health}%` }} /></div></div></td>
            <td>{statusBadge(asset)}</td>
            <td><button className="maintenance__row-button" aria-label={`${t('maint.review')} ${asset.id}`} onClick={() => setSelected(asset)}><Icon name="search" size={15} />{t('maint.review')}</button>{reviewed.has(asset.id) && <small className="maintenance__reviewed">{t('maint.reviewed')}</small>}</td>
          </tr>)}</tbody>
        </table>
      </div> : <p className="maintenance__empty">{t(page === 'work' ? 'maint.noQueue' : 'maint.noResults')}</p>}
      <p className="maintenance__table-note">{t('maint.tableScope')}</p>
    </section>
  )

  return <div className="maintenance">
    <div className="maintenance__layout" inert={selected !== null}>
      <a className="skiplink" href="#maintenance-main" onClick={(event) => { event.preventDefault(); heading.current?.focus() }}>{t('maint.skip')}</a>
      <aside className="maintenance__rail">
        <div className="maintenance__brand"><span className="maintenance__brand-mark" aria-hidden="true"><img src="/artwork/asset-reliability-mark.svg" alt="" width={37} height={37} /></span><div><strong>{t('maint.product')}</strong><span>{t('maint.subtitle')}</span></div></div>
        <p className="maintenance__rail-label">{t('maint.workspace')}</p>
        <nav aria-label={t('maint.menu')} className="maintenance__nav">{PAGES.map((item) => <button key={item} aria-current={page === item ? 'page' : undefined} onClick={() => setPage(item)}><Icon name={PAGE_ICONS[item]} size={19} /><span>{t(`maint.${item}`)}</span></button>)}</nav>
        <div className="maintenance__rail-secondary"><p className="maintenance__rail-label">{t('maint.manage')}</p><a href="./#/datasets"><Icon name="database" size={18} />{t('maint.sources')}</a><a href="./#/approvals"><Icon name="shield" size={18} />{t('maint.approvals')}</a></div>
        <div className="maintenance__rail-foot"><Icon name="shield" size={19} /><div><strong>{t('maint.human')}</strong><span>{t('maint.engine')}</span></div></div>
      </aside>
      <div className="maintenance__body">
        <header className="maintenance__topbar"><div className="maintenance__breadcrumb"><span>{t('maint.workspace')}</span><span aria-hidden="true">/</span><strong>{t(`maint.${page}`)}</strong></div><div className="maintenance__top-actions"><span className="maintenance__preview-tag">{t('maint.preview')}</span><button className="iconbtn" aria-label={isDark ? t('theme.toLight') : t('theme.toDark')} onClick={toggleTheme}><Icon name={isDark ? 'sun' : 'moon'} size={19} /></button><button className="maintenance__language" onClick={() => applyLocale(locale === 'en' ? 'ar' : 'en')} aria-label={t('language.switch')}><Icon name="globe" size={17} /><span lang={locale === 'en' ? 'ar' : 'en'}>{t('language.other')}</span></button></div></header>
        <main id="maintenance-main" className="maintenance__content">
          <div className="maintenance__sample"><span><Icon name="database" size={15} /><strong>{t('maint.sample')}</strong><span>{t('maint.notice')}</span></span><a href="./#/overview">{t('maint.liveLink')} <span aria-hidden="true">↗</span></a></div>
          <div className="maintenance__heading"><div><p className="maintenance__eyebrow">{t(`maint.${page}`)}</p><h1 ref={heading} tabIndex={-1}>{t(`maint.title.${page}`)}</h1><p>{t(`maint.description.${page}`)}</p></div><div className="maintenance__heading-actions"><a className="btn btn--primary" href="./#/runs?source=upload"><Icon name="plus" size={16} />{t('maint.upload')}</a><button className="btn btn--ghost" onClick={download}><Icon name="download" size={16} />{t('maint.export')}</button></div></div>
          <div className="maintenance__filters"><label><span>{t('maint.site')}</span><select value={site} onChange={(event) => setSite(event.target.value as Site | 'all')}><option value="all">{t('maint.allSites')}</option>{SITES.map((item) => <option value={item} key={item}>{t(`maint.${item}`)}</option>)}</select></label><label><span>{t('maint.period')}</span><select value={period} onChange={(event) => setPeriod(event.target.value as Period)}>{(['current', 'previous', 'all'] as const).map((value) => <option key={value} value={value}>{t(`maint.${value}`)}</option>)}</select></label><label className="maintenance__search"><span>{t('maint.search')}</span><input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder={t('maint.searchHint')} /></label><button className="maintenance__text-button" onClick={reset}>{t('maint.reset')}</button><span className="maintenance__scope" role="status">{t('maint.scope', { n: summary.count })}</span></div>
          <p role="status" className="visually-hidden">{notice}</p>
          {page === 'models' ? <>
            <section className="maintenance__model-empty"><span className="maintenance__model-icon"><Icon name="sparkle" size={30} /></span><p className="maintenance__eyebrow">{t('maint.models')}</p><h2>{t('maint.modelTitle')}</h2><p>{t('maint.modelBody')}</p><a className="btn btn--primary" href="./#/runs">{t('maint.openRuns')} <span aria-hidden="true">↗</span></a></section>
            <div className="maintenance__requirements">{(['Target', 'Timing', 'Baseline'] as const).map((item, i) => <section className="maintenance__panel" key={item}><span className="maintenance__step">0{i + 1}</span><h2>{t(`maint.model${item}`)}</h2><p>{t(`maint.model${item}Body`)}</p></section>)}</div>
          </> : !assets.length ? <section className="maintenance__model-empty"><Icon name="search" size={30} /><h2>{t('maint.noResults')}</h2><p>{t('maint.noResultsHint')}</p><button className="btn btn--primary" onClick={reset}>{t('maint.reset')}</button></section> : <>
            <section className="maintenance__metrics" aria-label={t('maint.overview')}>
              {([
                ['availability', summary.availability === null ? t('maint.noValue') : `${number(summary.availability, 1)}%`, 'availabilityNote', 'activity'],
                ['downtime', `${number(summary.downtime)} ${t('maint.hours')}`, 'downtimeNote', 'refresh'],
                ['spend', money(summary.cost), 'spendNote', 'database'],
                ['attention', number(summary.attention), 'attentionNote', 'alert'],
              ] as const).map(([key, value, note, icon]) => <article className={`maintenance__metric maintenance__metric--${key}`} key={key}><div><h2>{t(`maint.${key}`)}</h2><Icon name={icon} size={17} /></div><strong>{value}</strong><p>{t(`maint.${note}`)}</p></article>)}
            </section>
            {(page === 'overview' || page === 'reliability') && <div className="maintenance__charts">
              <section className="maintenance__panel"><div className="maintenance__panel-head"><div><h2>{t('maint.trend')}</h2><p>{t('maint.trendSub')}</p></div><span className="maintenance__unit">{t('maint.hours')}</span></div>
                <svg className="maintenance__trend" viewBox="0 0 600 220" role="img" aria-label={t('maint.trend')}>
                  {[0, 1, 2, 3].map((tick) => <g key={tick}><line x1="48" x2="548" y1={176 - tick * 46} y2={176 - tick * 46} /><text x="34" y={180 - tick * 46} textAnchor="end">{number(maxTrend * tick / 3)}</text></g>)}
                  <polygon points={`48,176 ${points.join(' ')} 548,176`} className="maintenance__area" />
                  <polyline points={points.join(' ')} className="maintenance__line" />
                  {summary.series.map((point, i) => <g key={point.month}><circle cx={48 + i * 500 / Math.max(1, summary.series.length - 1)} cy={176 - point.value / maxTrend * 138} r="4" /><text x={48 + i * 500 / Math.max(1, summary.series.length - 1)} y="205" textAnchor="middle">{month(point.month)}</text><text className="maintenance__point-label" x={48 + i * 500 / Math.max(1, summary.series.length - 1)} y={164 - point.value / maxTrend * 138} textAnchor="middle">{number(point.value)}</text></g>)}
                </svg>
                <details className="maintenance__chart-data"><summary>{t('maint.numbers')}</summary><table><thead><tr><th>{t('maint.month')}</th><th>{t('maint.downtime')} ({t('maint.hours')})</th></tr></thead><tbody>{summary.series.map((point) => <tr key={point.month}><th scope="row">{month(point.month)}</th><td>{number(point.value)}</td></tr>)}</tbody></table></details>
              </section>
              <section className="maintenance__panel"><div className="maintenance__panel-head"><div><h2>{t('maint.condition')}</h2><p>{t('maint.conditionSub')}</p></div><Icon name="activity" size={18} /></div><div className="maintenance__condition"><div className="maintenance__donut"><svg viewBox="0 0 160 160" aria-hidden="true">{CONDITIONS.map((condition, index) => {
                const count = assets.filter((asset) => severity(asset) === condition).length
                const previous = CONDITIONS.slice(0, index).reduce((sum, key) => sum + assets.filter((asset) => severity(asset) === key).length, 0)
                return <circle key={condition} className={`maintenance__ring--${condition}`} cx="80" cy="80" r="62" fill="none" strokeWidth="13" pathLength="100" strokeDasharray={`${count / assets.length * 100} ${100 - count / assets.length * 100}`} strokeDashoffset={-previous / assets.length * 100} transform="rotate(-90 80 80)" />
              })}</svg><div><strong>{number(assets.length)}</strong><span>{t('maint.equipment')}</span></div></div><ul className="maintenance__legend">{CONDITIONS.map((condition) => <li key={condition}><span className={`maintenance__dot maintenance__dot--${condition}`} /><span>{t(`maint.${condition}`)}</span><strong>{assets.filter((asset) => severity(asset) === condition).length}</strong></li>)}</ul></div><p className="maintenance__snapshot-note">{t('maint.thresholds')}</p></section>
            </div>}
            {page === 'cost' ? <section className="maintenance__panel maintenance__cost-panel"><div className="maintenance__panel-head"><div><h2>{t('maint.breakdown')}</h2><p>{t('maint.costNote')}</p></div><span className="maintenance__unit">{t('maint.usd')}</span></div>{SITES.filter((item) => assets.some((asset) => asset.site === item)).map((item) => {
              const cost = assets.filter((asset) => asset.site === item).reduce((sum, asset) => sum + assetCost(asset, period), 0)
              return <div className="maintenance__cost-row" key={item}><span>{t(`maint.${item}`)}</span><div aria-hidden="true"><i style={{ width: `${cost / summary.cost * 100}%` }} /></div><strong>{money(cost)}</strong></div>
            })}<table><caption>{t('maint.breakdown')}</caption><thead><tr><th>{t('maint.site')}</th><th>{t('maint.spend')} ({t('maint.usd')})</th></tr></thead><tbody>{SITES.filter((item) => assets.some((asset) => asset.site === item)).map((item) => <tr key={item}><th scope="row">{t(`maint.${item}`)}</th><td>{number(assets.filter((asset) => asset.site === item).reduce((sum, asset) => sum + assetCost(asset, period), 0))}</td></tr>)}</tbody></table></section> : <div className={page === 'overview' ? 'maintenance__lower' : ''}>{equipmentTable}{page === 'overview' && <aside className="maintenance__brief"><div className="maintenance__brief-head"><span><Icon name="sparkle" size={20} /></span><p>{t('maint.insightTag')}</p></div><h2>{t('maint.insight')}</h2><p>{leading && summary.downtime > 0 ? t('maint.insightText', { id: leading.id, share: number(assetDowntime(leading, period) / summary.downtime * 100, 1) }) : t('maint.insightEmpty')}</p>{leading && <button className="btn btn--primary" onClick={() => setSelected(leading)}>{t('maint.inspect')} <Icon name="search" size={15} /></button>}<div className="maintenance__human"><Icon name="shield" size={18} /><div><strong>{t('maint.human')}</strong><p>{t('maint.humanNote')}</p></div></div></aside>}</div>}
          </>}
          <details className="maintenance__method"><summary><Icon name="shield" size={16} />{t('maint.method')}</summary><p>{t('maint.methodBody')}</p><p>{t('maint.thresholds')}</p></details>
        </main>
      </div>
    </div>
    {selected && <Dialog title={`${t('maint.record')} · ${selected.id}`} onClose={closeEvidence} wide initialFocus="panel"><div className="maintenance__evidence"><p className="maintenance__evidence-tag">{t('maint.sample')}</p><div className="maintenance__record-heading"><div><h3>{t(`maint.${selected.kind}`)}</h3><p>{t(`maint.${selected.site}`)} · <bdi>{selected.id}</bdi></p></div>{statusBadge(selected)}</div><dl><div><dt>{t('maint.health')}</dt><dd>{healthValue(selected)}</dd></div><div><dt>{t('maint.downtime')}</dt><dd>{number(assetDowntime(selected, period))} {t('maint.hours')}</dd></div><div><dt>{t('maint.spend')}</dt><dd>{money(assetCost(selected, period))}</dd></div></dl><h3>{t('maint.method')}</h3><p>{t('maint.methodBody')}</p><p>{t('maint.thresholds')}</p><p className="maintenance__review-note">{t('maint.reviewNote')}</p>{reviewed.has(selected.id) && <p role="status">{t('maint.reviewed')}</p>}<div className="dialog__actions"><button className="btn btn--subtle" onClick={closeEvidence}>{t('maint.close')}</button><button className="btn btn--primary" disabled={reviewed.has(selected.id)} onClick={() => setReviewed((previous) => new Set([...previous, selected.id]))}><Icon name="check" size={16} />{t('maint.markReviewed')}</button></div></div></Dialog>}
  </div>
}
