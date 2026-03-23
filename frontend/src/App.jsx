import PropTypes from 'prop-types'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import Layout from './components/layout/Layout'
import LoginPage from './pages/LoginPage'
import HomePage from './pages/HomePage'
import CoursesPage from './pages/CoursesPage'
import CourseDetailPage from './pages/CourseDetailPage'
import LessonPage, { LearnRedirect } from './pages/LessonPage'
import MyLearningPage from './pages/MyLearningPage'
import AnalyticsPage from './pages/AnalyticsPage'
import PlaceholderPage from './pages/PlaceholderPage'
import AuthoringPage from './pages/AuthoringPage'
import CourseEditorPage from './pages/CourseEditorPage'
import CourseCreatePage from './pages/CourseCreatePage'
import ModuleEditorPage from './pages/ModuleEditorPage'

ContentCreatorRoute.propTypes = { element: PropTypes.node.isRequired }

function ContentCreatorRoute({ element }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  if (user.profile?.user_type !== 'content_creator') return <Navigate to="/" replace />
  return element
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<Layout />}>
            <Route index element={<HomePage />} />
            <Route path="/courses"              element={<CoursesPage />} />
            <Route path="/courses/:id"          element={<CourseDetailPage />} />
            <Route path="/learning"             element={<MyLearningPage />} />

            <Route path="/analytics"            element={<AnalyticsPage />} />
            <Route path="/profile"              element={<PlaceholderPage title="Profile" />} />
            <Route path="/authoring"                  element={<ContentCreatorRoute element={<AuthoringPage />} />} />
            <Route path="/authoring/courses/new"     element={<ContentCreatorRoute element={<CourseCreatePage />} />} />
            <Route path="/authoring/courses/:id"     element={<ContentCreatorRoute element={<CourseEditorPage />} />} />
            <Route path="/authoring/courses/:id/modules/:moduleId" element={<ContentCreatorRoute element={<ModuleEditorPage />} />} />
          </Route>
          {/* Lesson player — full-page, own layout (auth handled inside component) */}
          <Route path="/courses/:id/learn"           element={<LearnRedirect />} />
          <Route path="/courses/:courseId/learn/:lessonId" element={<LessonPage />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
