import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useLang, useT, type TextKey } from '../i18n'
import { api, type DocKind, type DocumentRow } from '../lib/api'
import { amd, date } from '../lib/format'
import { useSession } from '../lib/session'

type KindFilter = 'all' | 'invoice' | 'delivery_note' | 'acceptance_act' | 'src'
type Period = 'month' | 'prev' | 'all'

const KIND_FILTERS: { key: KindFilter; label: TextKey; kinds?: DocKind[] }[] = [
  { key: 'all', label: 'all_kinds' },
  { key: 'invoice', label: 'kind_invoice', kinds: ['invoice'] },
  { key: 'delivery_note', label: 'kind_delivery_note', kinds: ['delivery_note'] },
  { key: 'acceptance_act', label: 'kind_acceptance_act', kinds: ['acceptance_act'] },
  { key: 'src', label: 'kind_src', kinds: ['tax_invoice', 'waybill'] },
]
const PRINTABLE: DocKind[] = ['invoice', 'delivery_note', 'acceptance_act']
const KIND_SHORT: Record<string, string> = {
  invoice: 'INV',
  delivery_note: 'DN',
  acceptance_act: 'ACT',
  tax_invoice: 'SRC',
  waybill: 'SRC',
}

const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

function range(p: Period): { date_from?: string; date_to?: string } {
  const now = new Date()
  if (p === 'month') return { date_from: iso(new Date(now.getFullYear(), now.getMonth(), 1)) }
  if (p === 'prev')
    return {
      date_from: iso(new Date(now.getFullYear(), now.getMonth() - 1, 1)),
      date_to: iso(new Date(now.getFullYear(), now.getMonth(), 0)),
    }
  return {}
}

/** Every invoice, delivery note and act of the company, on the side it acts on now (purchases or sales). */
export function Documents() {
  const t = useT()
  const lang = useLang()
  const { mode } = useSession()
  const [kind, setKind] = useState<KindFilter>('all')
  const [period, setPeriod] = useState<Period>('all')
  const [q, setQ] = useState('')
  const [rows, setRows] = useState<DocumentRow[] | null>(null)
  const [picked, setPicked] = useState<Set<string>>(new Set())

  useEffect(() => {
    const timer = setTimeout(() => {
      api
        .documentRegister({ kind: KIND_FILTERS.find((k) => k.key === kind)?.kinds, q, ...range(period) })
        .then((r) => {
          setRows(r.items)
          setPicked(new Set())
        })
    }, 250)
    return () => clearTimeout(timer)
  }, [kind, period, q, mode])

  const printable = useMemo(() => (rows ?? []).filter((d) => PRINTABLE.includes(d.kind)), [rows])
  const toggle = (id: string) =>
    setPicked((s) => {
      const next = new Set(s)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })

  return (
    <div className="stack page" style={{ maxWidth: 980 }}>
      <h1 className="page-title">
        {t('tab_documents')}
        <small>{mode === 'seller' ? t('documents_sales') : t('documents_purchases')}</small>
      </h1>
      <input className="search" placeholder={t('search_documents')} value={q} onChange={(e) => setQ(e.target.value)} />
      <div className="chips" style={{ paddingBottom: 0 }}>
        {KIND_FILTERS.map((k) => (
          <button key={k.key} className={kind === k.key ? 'chip on' : 'chip'} onClick={() => setKind(k.key)}>
            {t(k.label)}
          </button>
        ))}
      </div>
      <div className="chips" style={{ paddingTop: 0 }}>
        {(['month', 'prev', 'all'] as Period[]).map((p) => (
          <button key={p} className={period === p ? 'chip toggle on' : 'chip toggle'} onClick={() => setPeriod(p)}>
            {t(p === 'month' ? 'period_month' : p === 'prev' ? 'period_prev' : 'period_all')}
          </button>
        ))}
      </div>

      {printable.length > 0 && (
        <div className="side-row">
          <label className="check">
            <input
              type="checkbox"
              checked={picked.size === printable.length}
              onChange={(e) => setPicked(e.target.checked ? new Set(printable.map((d) => d.id)) : new Set())}
            />
            {t('select_all')}
          </label>
          <a
            className={picked.size ? 'btn primary small-btn' : 'btn primary small-btn disabled'}
            href={picked.size ? `/print/batch?ids=${[...picked].join(',')}` : undefined}
            target="_blank"
            rel="noopener"
            aria-disabled={!picked.size}
          >
            🖨 {t('print_selected')} {picked.size ? `· ${picked.size}` : ''}
          </a>
        </div>
      )}

      {rows?.length === 0 && (
        <div className="col-empty" style={{ display: 'grid', gap: 6 }}>
          <span>{t('no_documents')}</span>
          <span className="small" style={{ fontWeight: 500 }}>
            {t('documents_hint')}
          </span>
        </div>
      )}
      <ul className="doc-list">
        {rows?.map((d) => {
          const canPrint = PRINTABLE.includes(d.kind)
          return (
            <li key={d.id} className="doc-row">
              {canPrint ? (
                <input type="checkbox" checked={picked.has(d.id)} onChange={() => toggle(d.id)} aria-label={d.number ?? d.kind} />
              ) : (
                <span style={{ width: 22 }} />
              )}
              <span className="doc-kind">{KIND_SHORT[d.kind]}</span>
              <span className="doc-main">
                <b className="num">{d.number ?? d.external_id ?? '—'}</b>
                <span className="muted small">
                  {d.counterparty} ·{' '}
                  <Link to={`/orders/${d.order_id}`} className="link small" style={{ padding: 0 }}>
                    {d.order_number}
                  </Link>
                </span>
              </span>
              <span className="doc-meta">
                <span className="num">{amd(d.order_total_amd)}</span>
                <span className="muted small">{d.issued_at ? date(d.issued_at, lang) : ''}</span>
              </span>
              {canPrint ? (
                <a className="ibtn" href={`/print/${d.id}`} target="_blank" rel="noopener" aria-label={t('print')}>
                  ↗
                </a>
              ) : (
                <span style={{ width: 40 }} />
              )}
            </li>
          )
        })}
      </ul>
    </div>
  )
}
