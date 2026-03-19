import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import Layout from './components/layout/Layout'
import LoginPage from './pages/LoginPage'
import HomePage from './pages/HomePage'
import PlaceholderPage from './pages/PlaceholderPage'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<Layout />}>
            <Route index element={<HomePage />} />
            <Route path="/courses"   element={<PlaceholderPage title="Courses" />} />
            <Route path="/learning"  element={<PlaceholderPage title="My Learning" />} />
            <Route path="/analytics" element={<PlaceholderPage title="Content Analytics" />} />
            <Route path="/profile"   element={<PlaceholderPage title="Profile" />} />
            <Route path="/authoring" element={<PlaceholderPage title="Authoring" />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
