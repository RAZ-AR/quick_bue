import { useLang, useT } from '../i18n'
import type { ClientProfile } from '../lib/api'
import { amd, date } from '../lib/format'
import { pct } from '../lib/haggle'

/** What the seller knows about this buyer before answering: history with this seller only. */
export function ClientCard({ name, c }: { name: string; c: ClientProfile }) {
  const t = useT()
  const lang = useLang()
  const source = c.source === 'seller_invited' ? t('client_seller_invited') : c.source === 'platform' ? t('client_platform') : null
  return (
    <div className="client-card">
      <div className="client-head">
        <span className="eyebrow">{t('client_title')}</span>
        <strong>{name}</strong>
        {source && <span className={c.source === 'seller_invited' ? 'pill brand' : 'pill plain'}>{source}</span>}
      </div>
      {c.orders === 0 ? (
        <p className="muted small">{t('client_new')}</p>
      ) : (
        <dl className="client-stats">
          <div>
            <dt>{t('client_orders')}</dt>
            <dd className="num">{c.orders}</dd>
          </div>
          <div>
            <dt>{t('client_avg')}</dt>
            <dd className="num">{amd(c.avg_order_amd)}</dd>
          </div>
          {c.first_order_at && (
            <div>
              <dt>{t('client_since')}</dt>
              <dd>{date(c.first_order_at.slice(0, 10), lang)}</dd>
            </div>
          )}
          {c.negotiated_orders > 0 ? (
            <>
              <div>
                <dt>{t('client_haggled')}</dt>
                <dd className="num">
                  {c.negotiated_orders} / {c.orders}
                </dd>
              </div>
              <div>
                <dt>{t('client_agreed')}</dt>
                <dd className="num">{c.agreed_orders}</dd>
              </div>
              <div>
                <dt>{t('client_avg_discount')}</dt>
                <dd className="num">−{pct(c.avg_discount_bp)}%</dd>
              </div>
            </>
          ) : (
            <div>
              <dt>{t('negotiation')}</dt>
              <dd>{t('client_never_haggled')}</dd>
            </div>
          )}
        </dl>
      )}
    </div>
  )
}
