/** Rounding that never lands a value on a whole number or zero it is not on.
 *  Two decimals by default; when that rounding would read 99.996 as 100 or
 *  0.004 as 0, more decimals (up to six) are kept until it does not, and a
 *  value smaller still keeps three significant digits. A value that is
 *  whole stays whole. Used for both the displayed and the spoken figure,
 *  so the two always agree. */
export function faithfulOptions(value: number): Intl.NumberFormatOptions {
  if (!Number.isFinite(value) || Number.isInteger(value)) return { maximumFractionDigits: 2 }
  for (let digits = 2; digits <= 6; digits += 1) {
    const scale = 10 ** digits
    if (!Number.isInteger(Math.round(value * scale) / scale)) return { maximumFractionDigits: digits }
  }
  return Math.abs(value) < 1 ? { maximumSignificantDigits: 3 } : { maximumFractionDigits: 6 }
}
