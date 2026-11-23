import { useState } from 'react'
import { Plus, X } from 'lucide-react'

interface TagInputProps {
  label: string
  value: string[]
  onChange: (value: string[]) => void
  placeholder?: string
  hint?: string
}

export function TagInput({ label, value, onChange, placeholder, hint }: TagInputProps) {
  const [draft, setDraft] = useState('')

  function addTag() {
    const cleaned = draft.trim().toLowerCase()
    if (!cleaned) return
    if (!value.includes(cleaned)) {
      onChange([...value, cleaned])
    }
    setDraft('')
  }

  return (
    <div className="tag-field">
      <div className="field-label-row">
        <span className="field-label">{label}</span>
        {hint ? <span className="field-hint">{hint}</span> : null}
      </div>
      <div className="tag-input-shell">
        <div className="tag-list">
          {value.map((tag) => (
            <span key={tag} className="tag">
              {tag}
              <button
                type="button"
                onClick={() => onChange(value.filter((item) => item !== tag))}
                aria-label={`Remove ${tag}`}
              >
                <X size={12} />
              </button>
            </span>
          ))}
          <input
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ',') {
                event.preventDefault()
                addTag()
              }
            }}
            placeholder={value.length === 0 ? placeholder : 'Add another…'}
          />
        </div>
        <button type="button" className="icon-button" onClick={addTag} aria-label={`Add ${label}`}>
          <Plus size={15} />
        </button>
      </div>
    </div>
  )
}
