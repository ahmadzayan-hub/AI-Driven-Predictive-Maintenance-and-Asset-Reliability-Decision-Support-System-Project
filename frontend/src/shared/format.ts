/* Formatting shared by more than one view. Numbers go through the
   locale's own formatter (`useI18n().formatNumber`), so digits and
   separators match the interface language. */

type FormatNumber = (value: number, options?: Intl.NumberFormatOptions) => string

/** A size in decimal units. The unit symbols stay Latin in both
 *  languages: they are symbols, not words. */
export function formatBytes(bytes: number, formatNumber: FormatNumber): string {
  if (bytes < 1000) return `${formatNumber(bytes)} B`
  if (bytes < 1_000_000) return `${formatNumber(bytes / 1000, { maximumFractionDigits: 1 })} kB`
  return `${formatNumber(bytes / 1_000_000, { maximumFractionDigits: 1 })} MB`
}

/** The three-letter ISO 4217 shape a stated currency has. */
export const CURRENCY_CODE = /^[A-Z]{3}$/

/** A money figure in the currency the owner stated in the column mapping,
 *  shown by its code ("AED 1,250,000.00") so two currencies never share a
 *  symbol. With no stated currency the bare number comes back and the
 *  caller adds the "currency not stated" label; a currency is never
 *  assumed. Arabic keeps Western digits like every other number here. */
export function formatMoney(
  value: number,
  currency: string | null | undefined,
  locale: 'en' | 'ar' = 'en',
  options?: Intl.NumberFormatOptions,
): string {
  const tag = locale === 'ar' ? 'ar-u-nu-latn' : 'en'
  const plain = () => new Intl.NumberFormat(tag, { maximumFractionDigits: 2, ...options }).format(value)
  if (!currency || !CURRENCY_CODE.test(currency)) return plain()
  try {
    return new Intl.NumberFormat(tag, { style: 'currency', currency, currencyDisplay: 'code', ...options }).format(value)
  } catch {
    // A code the runtime does not know still names the currency.
    return `${plain()} ${currency}`
  }
}
