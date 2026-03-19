import js from '@eslint/js'
import globals from 'globals'
import react from 'eslint-plugin-react' // <--- Add this
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'

export default [
  { ignores: ['dist/**'] },
  {
    files: ['**/*.{js,jsx}'],
    plugins: {
      react, // <--- Add this
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    languageOptions: {
      ecmaVersion: 2020,
      globals: {
        ...globals.browser,
      },
      parserOptions: {
        ecmaFeatures: { jsx: true },
        sourceType: 'module',
      },
    },
    settings: {
      react: { version: 'detect' }, // Recommended to detect React version
    },
    rules: {
      ...js.configs.recommended.rules,
      ...react.configs.recommended.rules, // <--- This handles JSX usage
      ...react.configs['jsx-runtime'].rules, // For modern React
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': 'warn',
      'no-unused-vars': ['error', { varsIgnorePattern: '^[A-Z_]' }],
    },
  },
]
