import { Fragment, useEffect, useState } from 'react'
import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'
import { inlineParts } from '../content/inline'

// Renders a legal text from content/<doc>/<lang>.js in the viewer's language
// (English when there's no file for it). `loaders` maps language → import().

Inline.propTypes = { text: PropTypes.string.isRequired }

function Inline({ text }) {
  return inlineParts(text).map((part, i) => {
    if (part.bold) return <strong key={i}>{part.bold}</strong>
    if (part.email) return <a key={i} href={`mailto:${part.email}`}>{part.email}</a>
    return <Fragment key={i}>{part.text}</Fragment>
  })
}

export default function LegalDocument({ loaders }) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language?.split('-')[0]
  const code = loaders[lang] ? lang : 'en'
  const [doc, setDoc] = useState(null)

  useEffect(() => {
    let alive = true
    loaders[code]()
      .catch(() => loaders.en())
      .then((module) => { if (alive) setDoc(module.default) })
    return () => { alive = false }
  }, [code, loaders])

  if (!doc) return <p>{t('common.loading')}</p>
  return (
    <>
      <p><Inline text={doc.intro} /></p>
      {doc.sections.map((section) => (
        <Fragment key={section.title}>
          <h2>{section.title}</h2>
          {section.blocks.map((block, i) => {
            if (block.ul) return <ul key={i}>{block.ul.map((item, j) => <li key={j}><Inline text={item} /></li>)}</ul>
            if (block.highlight) return <p key={i} className="legal-highlight"><Inline text={block.highlight} /></p>
            return <p key={i}><Inline text={block.p} /></p>
          })}
        </Fragment>
      ))}
    </>
  )
}

LegalDocument.propTypes = { loaders: PropTypes.objectOf(PropTypes.func).isRequired }
