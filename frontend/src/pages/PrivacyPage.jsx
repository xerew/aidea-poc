import { Fragment, useEffect, useState } from 'react'
import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'
import LegalLayout from '../components/LegalLayout'
import { inlineParts } from '../content/privacy/inline'

// The policy text lives in content/privacy/<lang>.js (English is the reference);
// only the viewer's language is loaded.
const LOADERS = {
  en: () => import('../content/privacy/en.js'),
  el: () => import('../content/privacy/el.js'),
  fr: () => import('../content/privacy/fr.js'),
  es: () => import('../content/privacy/es.js'),
  it: () => import('../content/privacy/it.js'),
  fi: () => import('../content/privacy/fi.js'),
  sv: () => import('../content/privacy/sv.js'),
  no: () => import('../content/privacy/no.js'),
  de: () => import('../content/privacy/de.js'),
}
const UPDATED = new Date(2026, 10, 1)   // November 2026: sign-in records, platform activity, Matomo user number

Inline.propTypes = { text: PropTypes.string.isRequired }

function Inline({ text }) {
  return inlineParts(text).map((part, i) => {
    if (part.bold) return <strong key={i}>{part.bold}</strong>
    if (part.email) return <a key={i} href={`mailto:${part.email}`}>{part.email}</a>
    return <Fragment key={i}>{part.text}</Fragment>
  })
}

export default function PrivacyPage() {
  const { t, i18n } = useTranslation()
  const lang = i18n.language?.split('-')[0]
  const code = LOADERS[lang] ? lang : 'en'
  const [doc, setDoc] = useState(null)

  useEffect(() => {
    let alive = true
    LOADERS[code]()
      .catch(() => LOADERS.en())
      .then((module) => { if (alive) setDoc(module.default) })
    return () => { alive = false }
  }, [code])

  return (
    <LegalLayout title={t('legal.privacyTitle')} updated={UPDATED}>
      {!doc ? <p>{t('common.loading')}</p> : (
        <>
          <p><Inline text={doc.intro} /></p>
          {doc.sections.map((section) => (
            <Fragment key={section.title}>
              <h2>{section.title}</h2>
              {section.blocks.map((block, i) => {
                if (block.ul) {
                  return <ul key={i}>{block.ul.map((item, j) => <li key={j}><Inline text={item} /></li>)}</ul>
                }
                if (block.highlight) return <p key={i} className="legal-highlight"><Inline text={block.highlight} /></p>
                return <p key={i}><Inline text={block.p} /></p>
              })}
            </Fragment>
          ))}
        </>
      )}
    </LegalLayout>
  )
}
