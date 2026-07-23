import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Checkbox } from '@/components/ui/checkbox'
import { Progress } from '@/components/ui/progress'
import { Label } from '@/components/ui/label'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'
import './OnboardingPage.css'

const STEP_DEFS = [
  {
    key: 'subject',
    i18nKey: 'subjectArea',
    type: 'subject',
  },
  {
    key: 'teaching_level',
    i18nKey: 'teachingLevel',
    type: 'radio',
    options: [
      { value: 'primary',    i18nKey: 'primary' },
      { value: 'secondary',  i18nKey: 'secondary' },
      { value: 'higher_ed',  i18nKey: 'higherEd' },
      { value: 'vocational', i18nKey: 'vocational' },
      { value: 'adult_ed',   i18nKey: 'adultEd' },
    ],
  },
  {
    key: 'goals',
    i18nKey: 'goals',
    type: 'multiselect',
    options: [
      { value: 'save_time',        i18nKey: 'saveTime' },
      { value: 'teach_about_ai',   i18nKey: 'teachAboutAi' },
      { value: 'prepare_students', i18nKey: 'prepareStudents' },
      { value: 'stay_current',     i18nKey: 'stayCurrent' },
      { value: 'address_ethics',   i18nKey: 'addressEthics' },
    ],
  },
]

export default function OnboardingPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { user, updateUser } = useAuth()
  const [step, setStep]       = useState(0)
  const [answers, setAnswers] = useState({})
  const [subjects, setSubjects] = useState([])
  const [questions, setQuestions] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')

  useEffect(() => {
    client.get('/subjects/').then(res => setSubjects(res.data)).catch(() => {})
    client.get('/onboarding/').then(res => setQuestions(res.data.questions ?? [])).catch(() => {})
  }, [])

  const resolveStatic = (s) => ({
    ...s,
    question: t(`onboarding.questions.${s.i18nKey}.question`),
    options: (s.options || []).map(o => ({
      ...o,
      label: t(`onboarding.questions.${s.i18nKey}.options.${o.i18nKey}`),
    })),
  })

  // Admin-editable competency questions (from the API) sit between the fixed
  // teaching-level step and the final goals step.
  const questionSteps = questions.map(q => ({
    key: `q_${q.id}`,
    type: 'question',
    questionId: q.id,
    question: q.text,
    options: q.options.map(o => ({ value: String(o.id), label: o.text })),
  }))

  const STEPS = [
    resolveStatic(STEP_DEFS[0]),  // subject
    resolveStatic(STEP_DEFS[1]),  // teaching level
    ...questionSteps,
    resolveStatic(STEP_DEFS[2]),  // goals
  ]

  const current = STEPS[step]
  const isLast  = step === STEPS.length - 1
  const hasAnswer = current.type === 'multiselect'
    ? true  // goals are optional — allow empty
    : !!answers[current.key]

  function handleRadio(value) {
    setAnswers(prev => ({ ...prev, [current.key]: value }))
  }

  function handleCheckbox(value, checked) {
    setAnswers(prev => {
      const vals = prev[current.key] || []
      return {
        ...prev,
        [current.key]: checked ? [...vals, value] : vals.filter(v => v !== value),
      }
    })
  }

  async function handleSubmit() {
    setLoading(true)
    setError('')
    try {
      const questionAnswers = {}
      questions.forEach(q => {
        const optionId = answers[`q_${q.id}`]
        if (optionId != null) questionAnswers[q.id] = Number(optionId)
      })
      await client.post('/onboarding/', {
        subject:        answers.subject,
        teaching_level: answers.teaching_level,
        answers:        questionAnswers,
        goals:          answers.goals || [],
      })
      updateUser({
        profile: { ...user.profile, onboarding_completed: true },
      })
      navigate('/')
    } catch (err) {
      setError(err.response?.data?.detail || t('onboarding.genericError'))
      setLoading(false)
    }
  }

  return (
    <div className="onboarding-container">
      <div className="onboarding-card">
        <div className="onboarding-header">
          <h1 className="onboarding-title">{t('onboarding.title')}</h1>
          <p className="onboarding-subtitle">
            {t('onboarding.subtitle')}
          </p>
          <Progress value={((step + 1) / STEPS.length) * 100} className="onboarding-progress" />
          <span className="onboarding-step-label">
            {t('onboarding.step', { current: step + 1, total: STEPS.length })}
          </span>
        </div>

        <div className="onboarding-question">
          <h2 className="onboarding-question-text">{current.question}</h2>

          {(current.type === 'radio' || current.type === 'question') && (
            <RadioGroup
              value={answers[current.key] || ''}
              onValueChange={handleRadio}
              className="onboarding-options"
            >
              {current.options.map(opt => (
                <div key={opt.value} className="onboarding-option">
                  <RadioGroupItem value={opt.value} id={`opt-${opt.value}`} />
                  <Label htmlFor={`opt-${opt.value}`} className="onboarding-option-label">
                    {opt.label}
                  </Label>
                </div>
              ))}
            </RadioGroup>
          )}

          {current.type === 'subject' && (
            <select
              className="onboarding-select"
              value={answers.subject || ''}
              onChange={e => setAnswers(prev => ({ ...prev, subject: e.target.value }))}
            >
              <option value="" disabled>{t('onboarding.selectSubject')}</option>
              {subjects.map(s => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          )}

          {current.type === 'multiselect' && (
            <div className="onboarding-options">
              {current.options.map(opt => (
                <div key={opt.value} className="onboarding-option">
                  <Checkbox
                    id={`goal-${opt.value}`}
                    checked={(answers[current.key] || []).includes(opt.value)}
                    onCheckedChange={checked => handleCheckbox(opt.value, checked)}
                  />
                  <Label htmlFor={`goal-${opt.value}`} className="onboarding-option-label">
                    {opt.label}
                  </Label>
                </div>
              ))}
            </div>
          )}
        </div>

        {error && <p className="onboarding-error">{error}</p>}

        <div className="onboarding-nav">
          {step > 0 && (
            <Button variant="outline" onClick={() => setStep(s => s - 1)} disabled={loading}>
              {t('common.back')}
            </Button>
          )}
          {!isLast && (
            <Button onClick={() => setStep(s => s + 1)} disabled={!hasAnswer}>
              {t('common.next')}
            </Button>
          )}
          {isLast && (
            <Button onClick={handleSubmit} disabled={loading}>
              {loading ? t('onboarding.building') : t('onboarding.completeSetup')}
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
