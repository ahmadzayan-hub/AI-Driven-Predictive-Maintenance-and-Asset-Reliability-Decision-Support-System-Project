import '../../shared/styles/analytics.css'
/** The dashboard's charts (ADR 0032): drawn as SVG or plain boxes from
 *  design tokens, no library. Each is an image with a text alternative;
 *  the numbers, and the way to the rows behind them, are in the table
 *  that every chart carries. Axes read left to right in both languages. */
import { useState, type ReactNode } from 'react'
import { useI18n } from '../../i18n'
import { usePack } from '../../i18n/pack'
import { dashMessages } from './messages'

export interface Point {
  label: string
  value: number | null
}

function span(values: number[]) {
  const max = Math.max(0, ...values)
  const min = Math.min(0, ...values)
  return { min, max, range: max - min || 1 }
}


/** A pointer tooltip for a chart's marks.
 *
 *  The numbers table under every figure stays the way to read a value
 *  exactly, and the way a keyboard or a screen reader reads it. This adds
 *  what a pointer expects: the value under the cursor, without leaving the
 *  chart. It is drawn inside the figure, so it cannot escape the page.
 */
function useTip() {
  const [tip, setTip] = useState<{ text: string; x: number; y: number } | null>(null)
  const show = (text: string) => (event: { currentTarget: Element; clientX: number; clientY: number }) => {
    const box = event.currentTarget.closest('.dash-plot')?.getBoundingClientRect()
    if (!box) return
    setTip({ text, x: event.clientX - box.left, y: event.clientY - box.top })
  }
  const hide = () => setTip(null)
  const node = tip
    ? <span className="dash-tip" style={{ insetInlineStart: `${tip.x}px`, top: `${Math.max(0, tip.y - 28)}px` }}>{tip.text}</span>
    : null
  return { show, hide, node }
}

/** A figure: its title, the chart, and the same numbers as a table. */
export function Figure({ title, chart, table, open = false }: {
  title: string
  chart: ReactNode
  table: ReactNode
  open?: boolean
}) {
  const { t, isRtl } = usePack(dashMessages)
  return (
    <figure className="dash-figure">
      <figcaption className="field__label" dir="auto">
        {title}
      </figcaption>
      <div dir="ltr" className="dash-plot">{chart}</div>
      <details className="runchart__data" dir={isRtl ? 'rtl' : 'ltr'} open={open}>
        <summary>{t('dash.numbers')}</summary>
        <div className="evidence__table" role="region" aria-label={title} tabIndex={0}>{table}</div>
      </details>
    </figure>
  )
}

/** Cross-filtering by clicking (ADR 2026-10-27-interactive-dashboard): a
 *  chart given `onPick` keeps the clicked group alone on every figure, or
 *  releases it when it is already the only one kept. Its marks are then
 *  buttons, pressed for the kept group, and the chart is a group rather
 *  than an image. */
export interface Pickable {
  onPick?: (label: string) => void
  picked?: (label: string) => boolean
}

/** Horizontal bars from a zero line, largest first as given. */
export function Bars({ items, label, onPick, picked }: { items: Point[]; label: string } & Pickable) {
  const { formatNumber } = useI18n()
  const { t } = usePack(dashMessages)
  const tip = useTip()
  const values = items.map((item) => item.value ?? 0)
  const { min, range } = span(values)
  const zero = (-min / range) * 100
  return (
    <div className="dash-bars" role={onPick ? 'group' : 'img'} aria-label={label}>
      {tip.node}
      {items.map((item, index) => {
        const value = values[index]
        const width = (Math.abs(value) / range) * 100
        const text = item.value === null ? '—' : formatNumber(item.value, { maximumFractionDigits: 2 })
        const reading = `${item.label || '—'} · ${text}`
        const held = picked?.(item.label) ?? false
        const Row = onPick ? 'button' : 'div'
        return (
          <Row
            className={`dash-bars__row${onPick ? ' dash-bars__row--pick' : ''}`}
            key={`${item.label}-${index}`}
            onMouseMove={tip.show(reading)}
            onMouseLeave={tip.hide}
            {...(onPick ? { type: 'button' as const, 'aria-pressed': held, 'aria-label': t(held ? 'dash.release' : 'dash.keep', { group: item.label || '—' }), onClick: () => onPick(item.label) } : {})}
          >
            <span className="dash-bars__label" dir="auto">
              {item.label || '—'}
            </span>
            <span className="dash-bars__track">
              <span
                className={`dash-bars__fill${value < 0 ? ' dash-bars__fill--negative' : ''}`}
                style={{ insetInlineStart: `${value < 0 ? zero - width : zero}%`, width: `${width}%` }}
              />
            </span>
            <span className="dash-bars__value">{text}</span>
          </Row>
        )
      })}
    </div>
  )
}

/** A line over periods; empty periods break the line. */
export function Line({ points, label, onPick, picked }: { points: Point[]; label: string } & Pickable) {
  const { formatNumber } = useI18n()
  const { t } = usePack(dashMessages)
  const tip = useTip()
  const values = points.map((p) => p.value).filter((v): v is number => v !== null)
  const { min, max, range } = span(values)
  // Compact Arabic values need room for both the number and its unit.
  const x = (index: number) => (points.length > 1 ? (index / (points.length - 1)) * 80 + 18 : 58)
  const y = (value: number) => 46 - ((value - min) / range) * 40
  const segments: string[][] = [[]]
  points.forEach((point, index) => {
    if (point.value === null) segments.push([])
    else segments[segments.length - 1].push(`${x(index)},${y(point.value)}`)
  })
  return (
    <>
    {tip.node}
    <svg viewBox="0 0 100 58" role={onPick ? 'group' : 'img'} aria-label={label} className="dash-svg">
      <line x1="18" y1={y(0)} x2="98" y2={y(0)} stroke="var(--border-strong)" strokeWidth="0.4" />
      {points.map((point, index) => {
        if (point.value === null) return null
        const held = picked?.(point.label) ?? false
        return (
          <circle
            key={`hit-${index}`}
            cx={x(index)}
            cy={y(point.value)}
            r="3"
            fill="transparent"
            className={held ? 'dash-point--held' : undefined}
            onMouseMove={tip.show(`${point.label} · ${formatNumber(point.value, { maximumFractionDigits: 2 })}`)}
            onMouseLeave={tip.hide}
            {...(onPick ? {
              role: 'button', tabIndex: 0, 'aria-pressed': held, 'aria-label': t(held ? 'dash.release' : 'dash.keep', { group: point.label }),
              onClick: () => onPick(point.label),
              onKeyDown: (event: { key: string; preventDefault: () => void }) => {
                if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onPick(point.label) }
              },
            } : {})}
          />
        )
      })}
      {segments.filter((s) => s.length > 1).map((segment, index) => (
        <polyline key={index} points={segment.join(' ')} fill="none" stroke="var(--accent-solid)" strokeWidth="1.2" pointerEvents="none" />
      ))}
      {points.length <= 40
        ? points.map((point, index) =>
            point.value === null ? null : (
              <circle key={index} cx={x(index)} cy={y(point.value)} r="0.9" fill="var(--accent-solid)" pointerEvents="none" />
            ),
          )
        : null}
      <text x="17" y={y(max) + 1} fontSize="3" textAnchor="end" fill="var(--text-faint)">
        {formatNumber(max, { notation: 'compact' })}
      </text>
      {min !== max ? (
        <text x="17" y={y(min) + 1} fontSize="3" textAnchor="end" fill="var(--text-faint)">
          {formatNumber(min, { notation: 'compact' })}
        </text>
      ) : null}
      <text x="18" y="55" fontSize="3.2" fill="var(--text-faint)">
        {points[0]?.label}
      </text>
      <text x="98" y="55" fontSize="3.2" textAnchor="end" fill="var(--text-faint)">
        {points[points.length - 1]?.label}
      </text>
    </svg>
    </>
  )
}

/** Counts per equal-width bin. With `onPick` each bin is a button: the
 *  range it stands for is kept alone on every figure, as a bar is (ADR
 *  2026-10-27-interactive-dashboard). */
export function Histogram({ bins, label, onPick, picked }: {
  bins: Array<{ from: number; to: number; count: number }>
  label: string
  onPick?: (index: number) => void
  picked?: (index: number) => boolean
}) {
  const { formatNumber } = useI18n()
  const { t } = usePack(dashMessages)
  const max = Math.max(1, ...bins.map((b) => b.count))
  const width = 92 / Math.max(bins.length, 1)
  return (
    <svg viewBox="0 0 100 58" role={onPick ? 'group' : 'img'} aria-label={label} className="dash-svg">
      {bins.map((bin, index) => {
        const height = (bin.count / max) * 44
        const x = 6 + index * width + width * 0.08
        const bar = (
          <rect className={picked?.(index) ? 'dash-bin__bar dash-bin__bar--held' : 'dash-bin__bar'}
            x={x} y={48 - height} width={width * 0.84} height={height} fill="var(--accent-solid)" rx="0.6" />
        )
        if (!onPick) return <g key={index}>{bar}</g>
        const held = picked?.(index) ?? false
        const group = `${formatNumber(bin.from, { maximumFractionDigits: 2 })} – ${formatNumber(bin.to, { maximumFractionDigits: 2 })}`
        return (
          <g key={index} role="button" tabIndex={0} aria-pressed={held}
            aria-label={t(held ? 'dash.release' : 'dash.keep', { group })}
            onClick={() => onPick(index)}
            onKeyDown={(event: { key: string; preventDefault: () => void }) => {
              if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onPick(index) }
            }}>
            {bar}
            <rect x={6 + index * width} y="0" width={width} height="50" fill="transparent" />
          </g>
        )
      })}
      <line x1="6" y1="48" x2="98" y2="48" stroke="var(--border-strong)" strokeWidth="0.4" />
      <text x="5" y="5" fontSize="3" textAnchor="end" fill="var(--text-faint)">{formatNumber(max)}</text>
      <text x="5" y="49" fontSize="3" textAnchor="end" fill="var(--text-faint)">{formatNumber(0)}</text>
      <text x="6" y="55" fontSize="3.2" fill="var(--text-faint)">
        {bins.length ? formatNumber(bins[0].from, { notation: 'compact' }) : ''}
      </text>
      <text x="98" y="55" fontSize="3.2" textAnchor="end" fill="var(--text-faint)">
        {bins.length ? formatNumber(bins[bins.length - 1].to, { notation: 'compact' }) : ''}
      </text>
    </svg>
  )
}

/** One point per sampled record. */
export function Scatter({ points, label }: { points: Array<{ x: number; y: number }>; label: string }) {
  const { formatNumber } = useI18n()
  const xs = span(points.map((p) => p.x))
  const ys = span(points.map((p) => p.y))
  return (
    <svg viewBox="0 0 100 58" role="img" aria-label={label} className="dash-svg">
      <line x1="18" y1="48" x2="98" y2="48" stroke="var(--border-strong)" strokeWidth="0.4" />
      <line x1="18" y1="4" x2="18" y2="48" stroke="var(--border-strong)" strokeWidth="0.4" />
      {points.map((point, index) => (
        <circle key={index} cx={18 + ((point.x - xs.min) / xs.range) * 80} cy={48 - ((point.y - ys.min) / ys.range) * 44}
          r="0.8" fill="var(--accent-solid)" fillOpacity="0.55" />
      ))}
      <text x="18" y="55" fontSize="3.2" fill="var(--text-faint)">{formatNumber(xs.min, { notation: 'compact' })}</text>
      <text x="98" y="55" fontSize="3.2" textAnchor="end" fill="var(--text-faint)">{formatNumber(xs.max, { notation: 'compact' })}</text>
      <text x="17" y="6" fontSize="3" textAnchor="end" fill="var(--text-faint)">{formatNumber(ys.max, { notation: 'compact' })}</text>
      <text x="17" y="49" fontSize="3" textAnchor="end" fill="var(--text-faint)">{formatNumber(ys.min, { notation: 'compact' })}</text>
    </svg>
  )
}
