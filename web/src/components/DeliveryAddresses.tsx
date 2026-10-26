import { useCallback, useEffect, useState } from 'react'
import { problemText, useLang, useT } from '../i18n'
import { api, ApiError, type Address, type AddressInput } from '../lib/api'
import { DISTRICTS } from '../lib/districts'
import { AddressField } from './AddressField'
import { ContactField } from './ContactField'
import { Field, SelectField } from './Field'

const EMPTY: AddressInput = {
  label: '',
  text: '',
  district: null,
  contact_name: null,
  contact_phone: null,
  delivery_notes: null,
}

/** Where orders go: several addresses, each with the person who receives the goods. */
export function DeliveryAddresses() {
  const t = useT()
  const [list, setList] = useState<Address[] | null>(null)
  const [editing, setEditing] = useState<Address | 'new' | null>(null)
  const [removing, setRemoving] = useState<string | null>(null)

  const load = useCallback(() => api.addresses().then(setList), [])
  useEffect(() => {
    void load()
  }, [load])

  return (
    <section className="ticket" id="addresses" style={{ display: 'grid', gap: 12 }}>
      <header className="ticket-head">
        <h2>{t('delivery_addresses')}</h2>
        {editing === null && (
          <button className="btn small primary" onClick={() => setEditing('new')}>
            + {t('add_address')}
          </button>
        )}
      </header>
      {list?.length === 0 && editing === null && <p className="muted small">{t('no_addresses')}</p>}
      <ul className="address-list">
        {list?.map((a) =>
          editing !== 'new' && editing?.id === a.id ? (
            <li key={a.id}>
              <AddressForm initial={a} onDone={async () => (setEditing(null), await load())} />
            </li>
          ) : (
            <li key={a.id} className="address-card">
              <div className="address-card-head">
                <strong>{a.label}</strong>
                {a.district && <span className="pill plain">{a.district}</span>}
              </div>
              <div>{a.text}</div>
              {(a.contact_name || a.contact_phone) && (
                <div className="small">
                  {t('receiver')}: {[a.contact_name, a.contact_phone].filter(Boolean).join(', ')}
                </div>
              )}
              {a.delivery_notes && <div className="muted small">💬 {a.delivery_notes}</div>}
              <div className="actions">
                {removing === a.id ? (
                  <>
                    <span className="small">{t('remove_address_q')}</span>
                    <button className="btn small ghost" onClick={() => setRemoving(null)}>
                      {t('cancel_edit')}
                    </button>
                    <button
                      className="btn small"
                      onClick={async () => (await api.removeAddress(a.id), setRemoving(null), await load())}
                    >
                      {t('remove')}
                    </button>
                  </>
                ) : (
                  <>
                    <button className="btn small ghost" onClick={() => setEditing(a)}>
                      {t('edit')}
                    </button>
                    <button className="btn small ghost" onClick={() => setRemoving(a.id)}>
                      {t('remove')}
                    </button>
                  </>
                )}
              </div>
            </li>
          ),
        )}
      </ul>
      {editing === 'new' && <AddressForm initial={EMPTY} onDone={async () => (setEditing(null), await load())} />}
    </section>
  )
}

function AddressForm({ initial, onDone }: { initial: AddressInput & { id?: string }; onDone: () => Promise<void> }) {
  const t = useT()
  const lang = useLang()
  const [f, setF] = useState<AddressInput>(initial)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)
  const set = (patch: Partial<AddressInput>) => setF((x) => ({ ...x, ...patch }))

  async function save(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setErrors({})
    try {
      if (initial.id) await api.editAddress(initial.id, f)
      else await api.addAddress(f)
      await onDone()
    } catch (err) {
      const byField: Record<string, string> = {}
      for (const p of (err as ApiError).problems ?? []) if (typeof p.field === 'string') byField[p.field] = problemText(p.code, lang)
      setErrors(byField)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="box" onSubmit={save}>
      <Field label={t('address_label')} placeholder={t('address_label_hint')} value={f.label} onChange={(e) => set({ label: e.target.value })} />
      <AddressField
        label={t('delivery_address')}
        required
        value={f.text}
        onChange={(text) => set({ text })}
        onResolved={(p) => setF((x) => ({ ...x, district: p.district ?? x.district, lat: p.lat, lng: p.lng }))}
        onDistrict={(district) => set({ district })}
        error={errors.text}
      />
      <SelectField
        label={t('district')}
        value={f.district ?? ''}
        onChange={(e) => set({ district: e.target.value || null })}
        options={[{ value: '', label: '—' }, ...DISTRICTS.map((d) => ({ value: d, label: d }))]}
      />
      <div className="form-grid tight">
        <Field label={t('receiver_name')} value={f.contact_name ?? ''} onChange={(e) => set({ contact_name: e.target.value })} />
        <ContactField kind="phone" label={t('receiver_phone')} value={f.contact_phone ?? ''} onChange={(v) => set({ contact_phone: v })} error={errors.contact_phone} />
      </div>
      <Field
        label={t('delivery_notes')}
        placeholder={t('delivery_notes_hint')}
        value={f.delivery_notes ?? ''}
        onChange={(e) => set({ delivery_notes: e.target.value })}
      />
      <div className="actions">
        <button type="button" className="btn ghost" onClick={() => void onDone()}>
          {t('cancel_edit')}
        </button>
        <button className="btn primary" disabled={busy}>
          {t('save')}
        </button>
      </div>
    </form>
  )
}
