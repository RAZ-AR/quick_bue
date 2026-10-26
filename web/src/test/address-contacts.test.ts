import streets from '../data/yerevan-streets.json'
import { checkContact, emailSuggestion, normalizePhone } from '../lib/contacts'
import { core, splitHouse, streetName, suggest, type Street } from '../lib/streets'

const all = streets as Street[]

describe('street suggestions', () => {
  it('finds a street typed in any language, without the street-type word', () => {
    for (const typed of ['Абовяна', 'улица Абовяна 1', 'abovyan', 'Աբովյան']) {
      expect(suggest(all, typed)[0]?.hy).toBe('Աբովյան փողոց')
    }
    expect(suggest(all, 'Комитаса')[0]?.hy).toBe('Կոմիտասի պողոտա')
    expect(suggest(all, 'а')).toEqual([])
  })

  it('splits the house number and names the street in the UI language', () => {
    expect(splitHouse('Абовяна 10/2')).toEqual({ street: 'Абовяна', house: '10/2' })
    expect(splitHouse('Абовяна')).toEqual({ street: 'Абовяна', house: null })
    const abovyan = all.find((s) => s.hy === 'Աբովյան փողոց')!
    expect([streetName(abovyan, 'ru'), abovyan.d]).toEqual(['улица Абовяна', ['Kentron']])
    expect(core('пр. Комитаса')).toBe('комитаса')
  })
})

describe('contacts', () => {
  it('formats Armenian phones and catches typos', () => {
    expect(normalizePhone('091 23-45-67')).toBe('+374 91 234 567')
    expect(normalizePhone('+7 912 345 67 89')).toBeNull()
    expect(emailSuggestion('ani@gmial.com')).toBe('ani@gmail.com')
    expect(checkContact('bank_account', '1570 0012 3456 7890')).toEqual({ value: '1570001234567890', problem: null })
    expect(checkContact('email', 'ani@')).toEqual({ value: null, problem: 'bad_email' })
    expect(checkContact('phone', '')).toEqual({ value: null, problem: null })
  })
})
