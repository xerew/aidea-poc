import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Search } from 'lucide-react'
import client from '../../api/client'
import './CourseSearch.css'

const MAX_RESULTS = 6

/** Header course search with a live, debounced autocomplete dropdown.
 *  Matches course title or description (published courses only). */
export default function CourseSearch() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(-1)
  const boxRef = useRef(null)
  const timerRef = useRef(null)

  // Debounced search — refreshes as the user types. Driven from the change
  // handler (not an effect) so state updates stay in event handlers.
  const handleChange = (e) => {
    const value = e.target.value
    setQuery(value)
    clearTimeout(timerRef.current)
    const q = value.trim()
    if (!q) { setResults([]); setOpen(false); return }
    timerRef.current = setTimeout(() => {
      client.get('/courses/', { params: { search: q } })
        .then((res) => { setResults(res.data.slice(0, MAX_RESULTS)); setActive(-1); setOpen(true) })
        .catch(() => setResults([]))
    }, 250)
  }

  // Close on outside click; clear any pending debounce on unmount.
  useEffect(() => {
    const onDoc = (e) => { if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', onDoc)
    return () => {
      document.removeEventListener('mousedown', onDoc)
      clearTimeout(timerRef.current)
    }
  }, [])

  const goToCourse = (course) => {
    setOpen(false)
    setQuery('')
    navigate(`/courses/${course.id}`)
  }

  const goToAll = () => {
    const q = query.trim()
    if (!q) return
    setOpen(false)
    navigate(`/courses?search=${encodeURIComponent(q)}`)
  }

  const onKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      if (open && active >= 0 && results[active]) goToCourse(results[active])
      else goToAll()
    } else if (e.key === 'Escape') {
      setOpen(false)
    } else if (open && results.length) {
      if (e.key === 'ArrowDown') { e.preventDefault(); setActive((i) => Math.min(i + 1, results.length - 1)) }
      else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((i) => Math.max(i - 1, -1)) }
    }
  }

  return (
    <div className="header-search" ref={boxRef}>
      <Search size={15} className="search-icon" />
      <input
        type="text"
        placeholder={t('common.search')}
        value={query}
        onChange={handleChange}
        onFocus={() => { if (results.length) setOpen(true) }}
        onKeyDown={onKeyDown}
        aria-label={t('common.search')}
        autoComplete="off"
      />
      {open && (
        <div className="search-dropdown">
          {results.length === 0 ? (
            <div className="search-empty">{t('search.noResults')}</div>
          ) : (
            results.map((course, i) => (
              <button
                key={course.id}
                type="button"
                className={`search-item${i === active ? ' search-item--active' : ''}`}
                onMouseEnter={() => setActive(i)}
                onMouseDown={(e) => { e.preventDefault(); goToCourse(course) }}
              >
                <span className="search-item-title">{course.title}</span>
                {course.pillar?.name && <span className="search-item-pillar">{course.pillar.name}</span>}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  )
}
