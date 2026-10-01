import { useEffect, useState } from 'react'
import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'
import { UsersRound, Plus, Trash2 } from 'lucide-react'
import client from '../../api/client'
import './CollaboratorsPanel.css'

const ROLES = ['co_editor', 'translator']

export default function CollaboratorsPanel({ courseId }) {
  const { t } = useTranslation()
  const [collaborators, setCollaborators] = useState([])
  const [query, setQuery] = useState('')
  const [candidates, setCandidates] = useState([])
  const [selected, setSelected] = useState(null)   // chosen candidate user
  const [role, setRole] = useState('co_editor')
  const [busy, setBusy] = useState(false)

  const load = () => {
    client.get(`/authoring/courses/${courseId}/collaborators/`)
      .then((res) => setCollaborators(res.data))
      .catch(() => {})
  }

  useEffect(() => { load() }, [courseId])   // eslint-disable-line react-hooks/exhaustive-deps

  // Debounced candidate search.
  useEffect(() => {
    const handle = setTimeout(() => {
      client.get('/authoring/collaborator-candidates/', { params: { q: query.trim() } })
        .then((res) => setCandidates(res.data))
        .catch(() => setCandidates([]))
    }, 250)
    return () => clearTimeout(handle)
  }, [query])

  const existingIds = new Set(collaborators.map((c) => c.user_id))
  const options = candidates.filter((c) => !existingIds.has(c.id))

  const add = async () => {
    if (!selected) return
    setBusy(true)
    try {
      await client.post(`/authoring/courses/${courseId}/collaborators/`,
        { user_id: selected.id, role })
      setSelected(null)
      setQuery('')
      load()
    } catch { /* ignore */ } finally { setBusy(false) }
  }

  const remove = async (userId) => {
    setBusy(true)
    try {
      await client.delete(`/authoring/courses/${courseId}/collaborators/${userId}/`)
      load()
    } catch { /* ignore */ } finally { setBusy(false) }
  }

  return (
    <section className="collab-panel">
      <h2 className="collab-title"><UsersRound size={18} /> {t('authoring.collab.title')}</h2>
      <p className="collab-desc">{t('authoring.collab.description')}</p>

      {collaborators.length === 0
        ? <p className="collab-empty">{t('authoring.collab.none')}</p>
        : (
          <ul className="collab-list">
            {collaborators.map((c) => (
              <li key={c.user_id} className="collab-row">
                <span className="collab-name">{c.name}</span>
                <span className={`collab-badge collab-badge--${c.role}`}>
                  {t(`authoring.collab.role.${c.role}`)}
                </span>
                <button
                  className="icon-btn icon-btn--danger"
                  onClick={() => remove(c.user_id)}
                  disabled={busy}
                  title={t('authoring.collab.remove')}
                >
                  <Trash2 size={15} />
                </button>
              </li>
            ))}
          </ul>
        )}

      <div className="collab-add">
        <div className="collab-search-wrap">
          <input
            className="collab-search"
            value={selected ? selected.name : query}
            placeholder={t('authoring.collab.searchPlaceholder')}
            onChange={(e) => { setSelected(null); setQuery(e.target.value) }}
          />
          {!selected && query.trim() && options.length > 0 && (
            <ul className="collab-candidates">
              {options.map((o) => (
                <li key={o.id}>
                  <button type="button" onClick={() => { setSelected(o); setQuery('') }}>
                    {o.name} <span className="collab-cand-user">@{o.username}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        <select className="collab-role" value={role} onChange={(e) => setRole(e.target.value)}>
          {ROLES.map((r) => <option key={r} value={r}>{t(`authoring.collab.role.${r}`)}</option>)}
        </select>
        <button type="button" className="collab-add-btn" onClick={add} disabled={!selected || busy}>
          <Plus size={15} /> {t('authoring.collab.add')}
        </button>
      </div>
    </section>
  )
}

CollaboratorsPanel.propTypes = {
  courseId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
}
