import PropTypes from 'prop-types'
import { useTranslation } from 'react-i18next'
import { Trash2, Plus } from 'lucide-react'
import { emptyQuestion } from './quizUtils'

export default function QuizBuilder({ quizData, textDisabled, structureLocked, onChange }) {
  const { t } = useTranslation()
  const questions = quizData ?? []

  const updateQuestion = (qi, text) => {
    const next = questions.map((q, i) => (i === qi ? { ...q, question: text } : q))
    onChange(next)
  }

  const updateOptionText = (qi, oi, text) => {
    const next = questions.map((q, i) =>
      i === qi
        ? { ...q, options: q.options.map((o, j) => (j === oi ? { ...o, text } : o)) }
        : q,
    )
    onChange(next)
  }

  const toggleCorrect = (qi, oi) => {
    const next = questions.map((q, i) =>
      i === qi
        ? { ...q, options: q.options.map((o, j) => (j === oi ? { ...o, is_correct: !o.is_correct } : o)) }
        : q,
    )
    onChange(next)
  }

  const addOption = (qi) => {
    const next = questions.map((q, i) =>
      i === qi ? { ...q, options: [...q.options, { text: '', is_correct: false }] } : q,
    )
    onChange(next)
  }

  const removeOption = (qi, oi) => {
    const next = questions.map((q, i) =>
      i === qi ? { ...q, options: q.options.filter((_, j) => j !== oi) } : q,
    )
    onChange(next)
  }

  const addQuestion = () => onChange([...questions, emptyQuestion()])

  const removeQuestion = (qi) => onChange(questions.filter((_, i) => i !== qi))

  return (
    <div className="quiz-builder">
      <h3 className="quiz-builder-title">{t('authoring.moduleEditor.quizBuilderTitle')}</h3>

      {questions.map((q, qi) => (
        <div key={qi} className="quiz-question">
          <div className="quiz-question-header">
            <input
              className="quiz-question-input"
              value={q.question}
              disabled={textDisabled}
              onChange={(e) => updateQuestion(qi, e.target.value)}
              placeholder={t('authoring.moduleEditor.questionPlaceholder', { number: qi + 1 })}
            />
            {!structureLocked && questions.length > 1 && (
              <button
                className="icon-btn icon-btn--danger"
                onClick={() => removeQuestion(qi)}
                title={t('authoring.moduleEditor.removeQuestion')}
              >
                <Trash2 size={14} />
              </button>
            )}
          </div>

          <div className="quiz-options">
            {q.options.map((opt, oi) => (
              <div key={oi} className="quiz-option">
                <input
                  type="checkbox"
                  className="quiz-option-checkbox"
                  checked={opt.is_correct}
                  disabled={structureLocked}
                  onChange={() => toggleCorrect(qi, oi)}
                  title={t('authoring.moduleEditor.markCorrect')}
                />
                <input
                  className="quiz-option-input"
                  value={opt.text}
                  disabled={textDisabled}
                  onChange={(e) => updateOptionText(qi, oi, e.target.value)}
                  placeholder={t('authoring.moduleEditor.optionPlaceholder', { letter: String.fromCharCode(65 + oi) })}
                />
                {!structureLocked && q.options.length > 2 && (
                  <button
                    className="icon-btn icon-btn--danger quiz-option-remove"
                    onClick={() => removeOption(qi, oi)}
                    title={t('authoring.moduleEditor.removeOption')}
                  >
                    <Trash2 size={12} />
                  </button>
                )}
              </div>
            ))}
          </div>

          {!structureLocked && (
            <button className="quiz-add-option-btn" onClick={() => addOption(qi)}>
              <Plus size={13} /> {t('authoring.moduleEditor.addOption')}
            </button>
          )}
        </div>
      ))}

      {!structureLocked && (
        <button className="quiz-add-question-btn" onClick={addQuestion}>
          <Plus size={14} /> {t('authoring.moduleEditor.addQuestion')}
        </button>
      )}
    </div>
  )
}

QuizBuilder.propTypes = {
  quizData: PropTypes.arrayOf(PropTypes.shape({
    question: PropTypes.string,
    options: PropTypes.arrayOf(PropTypes.shape({
      text: PropTypes.string,
      is_correct: PropTypes.bool,
    })),
  })).isRequired,
  textDisabled: PropTypes.bool.isRequired,
  structureLocked: PropTypes.bool.isRequired,
  onChange: PropTypes.func.isRequired,
}
