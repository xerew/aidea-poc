/* eslint-disable react-refresh/only-export-components */
import PropTypes from 'prop-types'
import { useState } from 'react'
import { Check, Eye, EyeOff, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import './PasswordInput.css'

export const PASSWORD_RULES = [
  { key: 'length', test: (p) => p.length >= 8 },
  { key: 'max',    test: (p) => p.length <= 128 },
  { key: 'upper',  test: (p) => /[A-Z]/.test(p) },
  { key: 'lower',  test: (p) => /[a-z]/.test(p) },
  { key: 'number', test: (p) => /\d/.test(p) },
  { key: 'symbol', test: (p) => /[^A-Za-z0-9]/.test(p) },
]

export function passwordStrength(password) {
  const passed = PASSWORD_RULES.filter(r => r.test(password)).length
  if (passed <= 2) return { key: 'weak',   color: '#dc2626' }
  if (passed === 3) return { key: 'fair',   color: '#f97316' }
  if (passed === 4) return { key: 'good',   color: '#eab308' }
  return               { key: 'strong', color: '#16a34a' }
}

export function PasswordInput({ value, onChange, placeholder, autoComplete }) {
  const { t } = useTranslation()
  const [visible, setVisible] = useState(false)
  return (
    <div className="pw-input-wrap">
      <input
        type={visible ? 'text' : 'password'}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        autoComplete={autoComplete}
        required
      />
      <button
        type="button"
        className="pw-eye-btn"
        onClick={() => setVisible(v => !v)}
        aria-label={visible ? t('auth.password.hidePassword') : t('auth.password.showPassword')}
      >
        {visible ? <EyeOff size={16} /> : <Eye size={16} />}
      </button>
    </div>
  )
}

PasswordInput.propTypes = {
  value:        PropTypes.string.isRequired,
  onChange:     PropTypes.func.isRequired,
  placeholder:  PropTypes.string,
  autoComplete: PropTypes.string,
}

export function PasswordStrengthPanel({ password }) {
  const { t } = useTranslation()
  if (!password) return null
  const strength = passwordStrength(password)
  const passed   = PASSWORD_RULES.filter(r => r.test(password)).length
  return (
    <>
      <div className="pw-strength-bar">
        <div
          className="pw-strength-fill"
          style={{
            width: `${(passed / PASSWORD_RULES.length) * 100}%`,
            background: strength.color,
          }}
        />
      </div>
      <span className="pw-strength-label" style={{ color: strength.color }}>
        {t(`auth.password.strength.${strength.key}`)}
      </span>
      <ul className="pw-rules">
        {PASSWORD_RULES.map(rule => {
          const met = rule.test(password)
          return (
            <li key={rule.key} className={`pw-rule ${met ? 'met' : 'unmet'}`}>
              {met ? <Check size={12} /> : <X size={12} />}
              {t(`auth.password.rules.${rule.key}`)}
            </li>
          )
        })}
      </ul>
    </>
  )
}

PasswordStrengthPanel.propTypes = {
  password: PropTypes.string.isRequired,
}
