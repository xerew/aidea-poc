import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Checkbox } from '@/components/ui/checkbox'
import { Progress } from '@/components/ui/progress'
import { Label } from '@/components/ui/label'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'
import './OnboardingPage.css'

const STEPS = [
  {
    key: 'subject_area',
    question: 'Which subject area do you primarily teach?',
    type: 'radio',
    options: [
      { value: 'stem',       label: 'STEM (Science, Technology, Engineering, Math)' },
      { value: 'humanities', label: 'Humanities & Social Sciences' },
      { value: 'languages',  label: 'Languages' },
      { value: 'arts',       label: 'Arts' },
      { value: 'general',    label: 'General / Multiple subjects' },
    ],
  },
  {
    key: 'teaching_level',
    question: 'What level do you teach?',
    type: 'radio',
    options: [
      { value: 'primary',    label: 'Primary (K–6)' },
      { value: 'secondary',  label: 'Secondary (7–12)' },
      { value: 'higher_ed',  label: 'Higher Education' },
      { value: 'vocational', label: 'Vocational' },
      { value: 'adult_ed',   label: 'Adult Education' },
    ],
  },
  {
    key: 'q3',
    question: "You ask an AI to summarise a student's essay. It gives a confident but factually wrong summary. What do you do?",
    type: 'radio',
    options: [
      { value: 'a', label: "Trust the AI — it's usually accurate" },
      { value: 'b', label: 'Check it yourself and correct it' },
      { value: 'c', label: 'Use a different AI tool instead' },
      { value: 'd', label: "I wouldn't use AI for this task" },
    ],
  },
  {
    key: 'q4',
    question: 'What does it mean when an AI model "hallucinates"?',
    type: 'radio',
    options: [
      { value: 'a', label: 'The AI crashes or freezes' },
      { value: 'b', label: 'The AI generates false information that sounds plausible' },
      { value: 'c', label: 'The AI gives creative or unexpected responses' },
      { value: 'd', label: "I'm not sure" },
    ],
  },
  {
    key: 'q5',
    question: 'Which of these is the best AI prompt for generating a lesson plan?',
    type: 'radio',
    options: [
      { value: 'a', label: '"Write a lesson plan"' },
      { value: 'b', label: '"Write a 45-minute lesson plan for 14-year-olds about fractions, include 3 activities"' },
      { value: 'c', label: '"Help me teach math"' },
      { value: 'd', label: '"I need a lesson plan about math, make it good"' },
    ],
  },
  {
    key: 'goals',
    question: 'What are your main learning goals? (Select all that apply)',
    type: 'multiselect',
    options: [
      { value: 'save_time',        label: 'Save time on lesson planning' },
      { value: 'teach_about_ai',   label: 'Learn to teach students about AI' },
      { value: 'prepare_students', label: 'Prepare students for an AI-driven world' },
      { value: 'stay_current',     label: 'Stay current with technology trends' },
      { value: 'address_ethics',   label: 'Address ethical concerns about AI' },
    ],
  },
]

export default function OnboardingPage() {
  const navigate = useNavigate()
  const { user, updateUser } = useAuth()
  const [step, setStep]       = useState(0)
  const [answers, setAnswers] = useState({})
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')

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
      navigate('/pathway')
    } catch (err) {
      setError(err.response?.data?.detail || 'Something went wrong. Please try again.')
      setLoading(false)
    }
  }

  return (
    <div className="onboarding-container">
      <div className="onboarding-card">
        <div className="onboarding-header">
          <h1 className="onboarding-title">Welcome to AIDEA</h1>
          <p className="onboarding-subtitle">
            Let&apos;s personalise your learning path. This takes about 2 minutes.
          </p>
          <Progress value={((step + 1) / STEPS.length) * 100} className="onboarding-progress" />
          <span className="onboarding-step-label">Step {step + 1} of {STEPS.length}</span>
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
              Back
            </Button>
          )}
          {!isLast && (
            <Button onClick={() => setStep(s => s + 1)} disabled={!hasAnswer}>
              Next
            </Button>
          )}
          {isLast && (
            <Button onClick={handleSubmit} disabled={loading}>
              {loading ? 'Building your learning path…' : 'Complete Setup'}
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
