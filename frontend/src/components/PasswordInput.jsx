/* eslint-disable react-refresh/only-export-components */
import PropTypes from 'prop-types'
import { useState } from 'react'
import { Check, Eye, EyeOff, X } from 'lucide-react'
import './PasswordInput.css'

export const PASSWORD_RULES = [
  { key: 'length', label: 'At least 8 characters',          test: (p) => p.length >= 8 },
  { key: 'max',    label: 'No more than 128 characters',    test: (p) => p.length <= 128 },
  { key: 'upper',  label: 'One uppercase letter (A–Z)',      test: (p) => /[A-Z]/.test(p) },
  { key: 'lower',  label: 'One lowercase letter (a–z)',      test: (p) => /[a-z]/.test(p) },
  { key: 'number', label: 'One number (0–9)',                test: (p) => /\d/.test(p) },
  { key: 'symbol', label: 'One special character (!@#$%…)',  test: (p) => /[^A-Za-z0-9]/.test(p) },
]

export function passwordStrength(password) {
  const passed = PASSWORD_RULES.filter(r => r.test(password)).length
  if (passed <= 2) return { label: 'Weak',   color: '#dc2626' }
  if (passed === 3) return { label: 'Fair',   color: '#f97316' }
  if (passed === 4) return { label: 'Good',   color: '#eab308' }
  return               { label: 'Strong', color: '#16a34a' }
}

export function PasswordInput({ value, onChange, placeholder, autoComplete }) {
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
        aria-label={visible ? 'Hide password' : 'Show password'}
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
        {strength.label}
      </span>
      <ul className="pw-rules">
        {PASSWORD_RULES.map(rule => {
          const met = rule.test(password)
          return (
            <li key={rule.key} className={`pw-rule ${met ? 'met' : 'unmet'}`}>
              {met ? <Check size={12} /> : <X size={12} />}
              {rule.label}
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
