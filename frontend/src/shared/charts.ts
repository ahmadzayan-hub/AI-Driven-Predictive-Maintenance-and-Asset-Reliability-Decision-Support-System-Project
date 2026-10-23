/* Geometry for the hand-drawn SVG charts. Kept apart from the components
   so that the arithmetic a reader trusts can be tested on its own. */

/** A vertical value scale that always contains zero, inside a band from
 *  `top` to `bottom` (SVG units, y grows downwards). The line a reader
 *  takes for zero must be drawn at zero: `zero` is where 0 falls, and
 *  `min` and `max` are the two values the axis is labelled with, so the
 *  extent of the scale is stated rather than implied. */
export function valueScale(values: number[], top: number, bottom: number) {
  const max = Math.max(0, ...values)
  const min = Math.min(0, ...values)
  const range = max - min || 1
  const y = (value: number) => bottom - ((value - min) / range) * (bottom - top)
  return { min, max, range, y, zero: y(0) }
}

/** Bars measured from zero in both directions, inside a band from `top`
 *  to `bottom` (SVG units, y grows downwards). A contribution chart holds
 *  decreases as well as increases; a bar drawn up from the bottom edge
 *  would give a negative value a negative height, and it would vanish. */
export function barGeometry(values: number[], top = 4, bottom = 50) {
  const max = Math.max(...values, 0)
  const min = Math.min(...values, 0)
  const span = max - min || 1
  const zero = top + (max / span) * (bottom - top)
  return {
    zero,
    bars: values.map((value) => {
      const height = (Math.abs(value) / span) * (bottom - top)
      return { y: value >= 0 ? zero - height : zero, height, negative: value < 0 }
    }),
  }
}
