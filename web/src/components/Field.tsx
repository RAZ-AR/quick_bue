import type React from 'react'

/** Labelled input in the pill style; `hint` sits under the label. */
export function Field({
  label,
  hint,
  error,
  ...input
}: { label: string; hint?: string; error?: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="field">
      <span>
        {label}
        {hint && <em className="muted" style={{ fontStyle: 'normal', fontWeight: 500 }}> · {hint}</em>}
      </span>
      <input {...input} />
      {error && <span className="error small">{error}</span>}
    </label>
  )
}

export function SelectField({
  label,
  options,
  ...select
}: { label: string; options: { value: string; label: string }[] } & React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <label className="field">
      <span>{label}</span>
      <select {...select}>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  )
}
