import { useId, useState } from 'react'
import { usePack } from '../../i18n/pack'
import { Dialog } from '../../shared/components/Dialog'
import { Icon } from '../../shared/components/Icon'
import { messages } from './messages'
import type { Asset, OperationsOverview } from './types'

/** Registry importance and recorded work are separate from measured condition. */
export function AssetInspector({ asset, data, onClose, onOpenRun }: {
  asset: Asset; data: OperationsOverview; onClose: () => void; onOpenRun: (id: string) => void
}) {
  const { t, formatDate, formatTime, formatNumber } = usePack(messages)
  const historyId = useId()
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const site = data.sites.find((item) => item.id === asset.site_id)
  const orders = data.work_orders.filter((order) => order.asset_id === asset.id)
  return <Dialog title={t('assetDetails')} onClose={onClose} wide initialFocus="panel" labelledById="operations-asset-title">
    <div className="operations__inspector">
      <header className="operations__asset-heading">
        <span className="operations__emblem"><Icon name="settings" size={26} /></span>
        <div><p className="operations__eyebrow">{t('asset')}</p><h3 dir="auto">{asset.name}</h3><p dir="auto">{site?.name ?? t('none')}</p></div>
      </header>
      <dl className="operations__asset-facts">
        <div><dt>{t('assetId')}</dt><dd><bdi>{asset.external_id}</bdi></dd></div>
        <div><dt>{t('sourceSystem')}</dt><dd dir="auto">{asset.source_system}</dd></div>
        <div><dt>{t('siteCode')}</dt><dd><bdi>{site?.code ?? t('none')}</bdi></dd></div>
        <div><dt>{t('criticality')}</dt><dd>{t(asset.criticality)}</dd></div>
      </dl>
      <div className="operations__context-note"><Icon name="help" size={18} /><p>{t('criticalityHelp')}</p></div>
      <section aria-labelledby="operations-asset-history">
        <div className="operations__section-heading"><h3 id="operations-asset-history">{t('assetWorkHistory')}</h3><span className="operations__count">{formatNumber(orders.length)}</span></div>
        <p className="operations__muted">{t('assetHistoryScope')}</p>
        {data.work_orders_truncated && <p className="operations__scope-note">{t('assetHistoryPartial', { shown: data.work_orders.length, total: data.work_order_count })}</p>}
        {!orders.length && <div className="operations__empty operations__empty--compact"><Icon name="clock" size={24} /><h4>{t('assetNoOrders')}</h4><p>{t('assetNoOrdersHelp')}</p></div>}
        <div className="operations__asset-history">{orders.map((order) => <article className="operations__history-order" key={order.id}>
          <h4><button type="button" className="operations__history-toggle" aria-expanded={expanded.has(order.id)} aria-controls={expanded.has(order.id) ? `${historyId}-${order.id}` : undefined} onClick={() => setExpanded((current) => {
            const next = new Set(current); if (next.has(order.id)) next.delete(order.id); else next.add(order.id); return next
          })}><span dir="auto">{order.title}</span><span className="operations__status">{t(order.status)}</span><Icon name="arrowDown" size={16} /></button></h4>
          {expanded.has(order.id) && <div className="operations__history-body" id={`${historyId}-${order.id}`}>
            <p dir="auto">{order.rationale}</p>
            <dl className="operations__asset-facts">
              <div><dt>{t('priority')}</dt><dd>{t(order.priority)}</dd></div>
              <div><dt>{t('assignee')}</dt><dd dir="auto">{order.assignee ?? t('unassigned')}</dd></div>
              <div><dt>{t('due')}</dt><dd><bdi>{order.due_date ?? t('none')}</bdi></dd></div>
              <div><dt>{t('orderReference')}</dt><dd><bdi>{order.id}</bdi></dd></div>
            </dl>
            <section className="operations__history-evidence" aria-label={t('evidence')}>
              <h4>{t('evidence')}</h4>
              <p>{t('records', { n: order.evidence.matching_records })}</p>
              <dl className="operations__asset-facts">
                <div><dt>{t('run')}</dt><dd><bdi>{order.evidence.run_id}</bdi></dd></div>
                <div><dt>{t('column')}</dt><dd><bdi>{order.evidence.asset_column}</bdi></dd></div>
                <div><dt>{t('assetId')}</dt><dd><bdi>{order.evidence.source_asset_id}</bdi></dd></div>
                <div><dt>{t('evidenceCaptured')}</dt><dd><time dateTime={order.evidence.captured_at}>{formatDate(order.evidence.captured_at)} {formatTime(order.evidence.captured_at)}</time></dd></div>
              </dl>
              <button type="button" className="btn btn--ghost" onClick={() => { onClose(); onOpenRun(order.evidence.run_id) }}>{t('openRun')}</button>
            </section>
            {order.status === 'completed' && <section aria-label={t('completion')}>
              <h4>{t('completion')}</h4>
              <p dir="auto">{order.completion.outcome || t('none')}</p><p dir="auto">{order.completion.notes || t('none')}</p>
              <dl className="operations__asset-facts"><div><dt>{t('labor')}</dt><dd>{order.completion.labor_hours == null ? t('none') : formatNumber(order.completion.labor_hours)}</dd></div></dl>
              <h4>{t('parts')}</h4>
              {order.completion.parts?.length ? <ul>{order.completion.parts.map((part, index) => <li key={index}><bdi>{part.part}</bdi> × <bdi>{formatNumber(part.quantity)}</bdi></li>)}</ul> : <p>{t('none')}</p>}
              <p className="operations__muted">{t('outcomeHelp')}</p>
            </section>}
            <section aria-label={t('audit')}><h4>{t('audit')}</h4>
              {!order.audit.length ? <p>{t('none')}</p> : <ol className="operations__audit">{order.audit.map((entry) => <li key={entry.id}>
                <strong>{['draft', 'created', 'updated', 'authorized', 'in_progress', 'completed', 'cancelled', 'assigned'].includes(entry.action.replace(/^work_/, '')) ? t(entry.action.replace(/^work_/, '') as 'created') : t('historyEntry')}</strong>
                <span dir="auto">{entry.actor}</span><span>{t('version', { n: entry.version })}</span><time dateTime={entry.created_at}>{formatDate(entry.created_at)} {formatTime(entry.created_at)}</time>
              </li>)}</ol>}
            </section>
          </div>}
        </article>)}</div>
      </section>
      <div className="operations__inspector-actions"><button type="button" className="btn btn--primary" onClick={onClose}>{t('closeAsset')}</button></div>
    </div>
  </Dialog>
}
