import { useState } from 'react'
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
    key: 'subject_area',
    i18nKey: 'subjectArea',
    type: 'radio',
    options: [
      { value: 'stem',       i18nKey: 'stem' },
      { value: 'humanities', i18nKey: 'humanities' },
      { value: 'languages',  i18nKey: 'languages' },
      { value: 'arts',       i18nKey: 'arts' },
      { value: 'general',    i18nKey: 'general' },
    ],
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
    key: 'q3',
    i18nKey: 'q3',
    type: 'radio',
    options: [
      { value: 'a', i18nKey: 'a' },
      { value: 'b', i18nKey: 'b' },
      { value: 'c', i18nKey: 'c' },
      { value: 'd', i18nKey: 'd' },
    ],
  },
  {
    key: 'q4',
    i18nKey: 'q4',
    type: 'radio',
    options: [
      { value: 'a', i18nKey: 'a' },
      { value: 'b', i18nKey: 'b' },
      { value: 'c', i18nKey: 'c' },
      { value: 'd', i18nKey: 'd' },
    ],
  },
  {
    key: 'q5',
    i18nKey: 'q5',
    type: 'radio',
    options: [
      { value: 'a', i18nKey: 'a' },
      { value: 'b', i18nKey: 'b' },
      { value: 'c', i18nKey: 'c' },
      { value: 'd', i18nKey: 'd' },
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
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')

  const STEPS = STEP_DEFS.map(s => ({
    ...s,
    question: t(`onboarding.questions.${s.i18nKey}.question`),
    options: s.options.map(o => ({
      ...o,
      label: t(`onboarding.questions.${s.i18nKey}.options.${o.i18nKey}`),
    })),
  }))

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
      await client.post('/onboarding/', {
        subject_area:   answers.subject_area,
        teaching_level: answers.teaching_level,
        answers:        { q3: answers.q3, q4: answers.q4, q5: answers.q5 },
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

          {current.type === 'radio' && (
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
