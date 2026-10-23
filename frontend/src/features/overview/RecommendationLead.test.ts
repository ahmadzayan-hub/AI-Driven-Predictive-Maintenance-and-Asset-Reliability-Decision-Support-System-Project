import { expect, it } from 'vitest'
import { recommendationLead } from './CommandCentre'

it('keeps short source text unchanged including its caveat', () => {
  const text = 'Review maintenance, but do not authorize execution.'
  expect(recommendationLead(text, 'Recommendation')).toBe(text)
})
it.each(['Review the observed asset maintenance exposure.', 'راجع الأثر المرصود لصيانة الأصول.'])('uses only an exact complete source sentence: %s', lead => {
  expect(recommendationLead(`${lead} ${'Important source limitation. '.repeat(20)}`, 'Recommendation')).toBe(lead)
})
it('uses a truthful label rather than clipping a long sentence', () => {
  expect(recommendationLead('A'.repeat(300), 'Full recommendation')).toBe('Full recommendation')
})
