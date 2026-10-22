import { createElement, useMemo } from 'react'
import type { CSSProperties, ReactNode, Ref } from 'react'

export interface ReportDocumentProps {
  content: string
  language: 'en' | 'ar'
  label: string
  className?: string
  ref?: Ref<HTMLDivElement>
}

// Generated reports use a deliberately small Markdown dialect. Unsupported or
// oversized content stays visible as text; limits never discard report data.
const MAX_CONTENT = 200_000
const MAX_LINES = 4_000
const MAX_BLOCKS = 1_000
const MAX_INLINE = 16_000
const MAX_COLUMNS = 32
const MAX_ROWS = 200

const textDirection = (value: string) => /\p{N}/u.test(value) && !/\p{L}/u.test(value) ? 'ltr' : 'auto'

function inline(source: string, depth = 0): ReactNode[] {
  if (source.length > MAX_INLINE || depth >= 4) return [source]
  const result: ReactNode[] = []
  let text = ''
  let cursor = 0
  let tokens = 0
  let lineEnd = source.indexOf('\n')
  let tagEnd = source.indexOf('>')
  let bracketEnd = source.indexOf(']')
  let linkEnd = bracketEnd < 0 ? -1 : source.indexOf(')', bracketEnd + 2)
  const flush = () => { if (text) { result.push(text); text = '' } }
  while (cursor < source.length && tokens < 256) {
    const char = source[cursor]
    if (char === '\\' && /[\\*`|[\]]/.test(source[cursor + 1] ?? '')) {
      text += source[cursor + 1]; cursor += 2; continue
    }
    // Cache closing positions: repeated unmatched openers must not rescan
    // the remaining paragraph once per character. No URL-bearing elements.
    if (lineEnd >= 0 && lineEnd < cursor) lineEnd = source.indexOf('\n', cursor)
    const endOfLine = lineEnd < 0 ? source.length : lineEnd
    if (char === '<') {
      if (tagEnd >= 0 && tagEnd < cursor) tagEnd = source.indexOf('>', cursor)
      if (tagEnd >= cursor && tagEnd < endOfLine) {
        text += source.slice(cursor, tagEnd + 1); cursor = tagEnd + 1; continue
      }
    }
    if (char === '[' || (char === '!' && source[cursor + 1] === '[')) {
      if (bracketEnd >= 0 && bracketEnd < cursor) {
        bracketEnd = source.indexOf(']', cursor)
        linkEnd = bracketEnd < 0 ? -1 : source.indexOf(')', bracketEnd + 2)
      }
      if (bracketEnd >= cursor && source[bracketEnd + 1] === '(' && linkEnd >= 0 && linkEnd < endOfLine) {
        text += source.slice(cursor, linkEnd + 1); cursor = linkEnd + 1; continue
      }
    }
    if (char === '`' || char === '*') {
      const delimiter = char === '`' ? /^`+/.exec(source.slice(cursor))![0] : source.startsWith('**', cursor) ? '**' : '*'
      const end = source.indexOf(delimiter, cursor + delimiter.length)
      if (end > cursor + delimiter.length) {
        flush()
        const value = source.slice(cursor + delimiter.length, end)
        result.push(char === '`'
          ? <code key={cursor}><bdi dir={textDirection(value)}>{value}</bdi></code>
          : createElement(delimiter === '**' ? 'strong' : 'em', { key: cursor }, inline(value, depth + 1)))
        cursor = end + delimiter.length; tokens += 1; continue
      }
      text += delimiter; cursor += delimiter.length; continue
    }
    if (char === '\n') { flush(); result.push(<br key={cursor} />); tokens += 1 }
    else text += char
    cursor += 1
  }
  text += source.slice(cursor)
  flush()
  return result
}

/** Split only structural pipes; keep escaped pipes and code contents intact. */
function cells(line: string): string[] | null {
  const source = line.trim()
  if (source.length > MAX_INLINE) return null
  const result: string[] = []
  let value = ''
  let code = ''
  let escaped = false
  let lastPipe = -1
  for (let index = 0; index < source.length; index += 1) {
    const char = source[index]
    if (escaped) { value += char; escaped = false; continue }
    if (char === '\\') { value += char; escaped = true; continue }
    if (char === '`') {
      const delimiter = /^`+/.exec(source.slice(index))![0]
      if (!code) code = delimiter
      else if (code === delimiter) code = ''
      value += delimiter; index += delimiter.length - 1; continue
    }
    if (char === '|' && !code) {
      result.push(value.trim()); value = ''; lastPipe = index
      if (result.length > MAX_COLUMNS + 1) return null
    } else value += char
  }
  if (lastPipe < 0) return null
  result.push(value.trim())
  if (source.startsWith('|')) result.shift()
  if (lastPipe === source.length - 1) result.pop()
  return result.length && result.length <= MAX_COLUMNS ? result : null
}

function tableHeader(lines: string[], index: number) {
  const header = cells(lines[index] ?? '')
  const separators = cells(lines[index + 1] ?? '')
  if (!header || !separators || header.length !== separators.length || !separators.every((cell) => /^:?-{3,}:?$/.test(cell))) return null
  const align = separators.map((cell): CSSProperties['textAlign'] => cell.startsWith(':')
    ? cell.endsWith(':') ? 'center' : 'left' : cell.endsWith(':') ? 'right' : undefined)
  return { header, align }
}

const heading = (line: string) => /^ {0,3}(#{1,6})\s+(.+)$/.exec(line)
const fence = (line: string) => /^ {0,3}(`{3,}|~{3,})(.*)$/.exec(line)
const listItem = (line: string) => /^(?:([-+*])|(\d{1,9})[.)])\s+(.*)$/.exec(line)
const rule = (line: string) => /^ {0,3}(?:(?:\*\s*){3,}|(?:-\s*){3,}|(?:_\s*){3,})$/.test(line)
const quote = (line: string) => /^>\s?(.*)$/.exec(line)
const literal = (content: string, key: number) => <pre className="report-document__literal" key={key}>{content}</pre>

function blocks(content: string, label: string): ReactNode[] {
  if (content.length > MAX_CONTENT) return [literal(content, 0)]
  const lines = content.split(/\r?\n/)
  const result: ReactNode[] = []
  const limit = Math.min(lines.length, MAX_LINES)
  let index = 0
  let caption = label
  const startsBlock = (at: number) => heading(lines[at]) || fence(lines[at]) || rule(lines[at])
    || listItem(lines[at]) || quote(lines[at]) || tableHeader(lines, at)
  while (index < limit && result.length < MAX_BLOCKS) {
    const start = index
    const line = lines[index]
    if (!line.trim()) { index += 1; continue }
    if (line.length > MAX_INLINE) { result.push(literal(line, start)); index += 1; continue }
    const code = fence(line)
    if (code) {
      index += 1
      const from = index
      while (index < limit) {
        const close = /^ {0,3}(`{3,}|~{3,})\s*$/.exec(lines[index])
        if (close && close[1][0] === code[1][0] && close[1].length >= code[1].length) break
        index += 1
      }
      const body = lines.slice(from, index).join('\n') + (index > from && index < lines.length ? '\n' : '')
      result.push(<pre className="report-document__code" key={start} dir="ltr" tabIndex={0}><code>{body}</code></pre>)
      if (index < limit) index += 1
      continue
    }
    const title = heading(line)
    if (title) {
      caption = title[2]
      result.push(createElement(`h${Math.min(6, title[1].length + 1)}`, { key: start }, inline(title[2])))
      index += 1; continue
    }
    if (rule(line)) { result.push(<hr key={start} />); index += 1; continue }
    const table = index + 1 < limit ? tableHeader(lines, index) : null
    if (table) {
      index += 2
      const rows: string[][] = []
      while (index < limit && rows.length < MAX_ROWS) {
        const row = cells(lines[index])
        // Keep malformed/extra cells in the subsequent literal paragraph.
        if (!row || row.length !== table.header.length) break
        rows.push(row); index += 1
      }
      result.push(<div className="report-document__table" key={start} role="region" aria-label={caption} tabIndex={0}>
        <table><caption>{inline(caption)}</caption>
          <thead><tr>{table.header.map((cell, column) => <th key={column} scope="col" style={{ textAlign: table.align[column] }}><bdi dir={textDirection(cell)}>{inline(cell)}</bdi></th>)}</tr></thead>
          <tbody>{rows.map((row, rowIndex) => <tr key={rowIndex}>{row.map((cell, column) => <td key={column} style={{ textAlign: table.align[column] }}><bdi dir={textDirection(cell)}>{inline(cell)}</bdi></td>)}</tr>)}</tbody>
        </table>
      </div>)
      continue
    }
    const item = listItem(line)
    if (item) {
      const ordered = Boolean(item[2])
      const items: ReactNode[] = []
      while (index < limit) {
        const next = listItem(lines[index])
        if (!next || Boolean(next[2]) !== ordered || rule(lines[index])) break
        items.push(<li key={index} value={ordered ? Number(next[2]) : undefined}>{inline(next[3])}</li>)
        index += 1
      }
      result.push(ordered ? <ol key={start} start={Number(item[2])}>{items}</ol> : <ul key={start}>{items}</ul>)
      continue
    }
    if (quote(line)) {
      const quoted: string[] = []
      while (index < limit) {
        const next = quote(lines[index])
        if (!next) break
        quoted.push(next[1]); index += 1
      }
      result.push(<blockquote key={start}><p>{inline(quoted.join('\n'))}</p></blockquote>)
      continue
    }
    index += 1
    while (index < limit && lines[index].trim() && !startsBlock(index)) index += 1
    result.push(<p key={start}>{inline(lines.slice(start, index).join('\n'))}</p>)
  }
  if (index < lines.length) result.push(literal(lines.slice(index).join('\n'), index))
  return result
}

/** Render a report without interpreting HTML, images or navigable links. */
export function ReportDocument({ content, language, label, className, ref }: ReportDocumentProps) {
  const rendered = useMemo(() => blocks(content, label), [content, label])
  return <div ref={ref} role="region" aria-label={label} lang={language} dir={language === 'ar' ? 'rtl' : 'ltr'} tabIndex={0}
    className={['runreport', 'report-document', className].filter(Boolean).join(' ')}>{rendered}</div>
}

export default ReportDocument
