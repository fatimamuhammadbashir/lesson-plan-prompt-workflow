import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { ToastProvider } from './components/ToastProvider'
import CurriculumPage from './pages/CurriculumPage'
import NewPlanLayout from './pages/NewPlanLayout'
import NotFound from './pages/NotFound'
import OverviewPage from './pages/OverviewPage'
import PlanLayout from './pages/PlanLayout'
import PlansPage from './pages/PlansPage'
import ReviewQueuePage from './pages/ReviewQueuePage'
import ContextStep from './pages/newplan/ContextStep'
import LearnersStep from './pages/newplan/LearnersStep'
import ReviewStep from './pages/newplan/ReviewStep'
import PlanActivities from './pages/plan/PlanActivities'
import PlanDecision from './pages/plan/PlanDecision'
import PlanEdit from './pages/plan/PlanEdit'
import PlanOverview from './pages/plan/PlanOverview'
import PlanReview from './pages/plan/PlanReview'

export default function App() {
  return (
    <ToastProvider>
      <AppShell>
        <Routes>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/plans" element={<PlansPage />} />
          <Route path="/reviews" element={<ReviewQueuePage />} />
          <Route path="/curriculum" element={<CurriculumPage />} />

          <Route path="/plans/new" element={<NewPlanLayout />}>
            <Route index element={<Navigate to="context" replace />} />
            <Route path="context" element={<ContextStep />} />
            <Route path="learners" element={<LearnersStep />} />
            <Route path="review" element={<ReviewStep />} />
          </Route>

          <Route path="/plans/:planId" element={<PlanLayout />}>
            <Route index element={<PlanOverview />} />
            <Route path="activities" element={<PlanActivities />} />
            <Route path="review" element={<PlanReview />} />
            <Route path="decide" element={<PlanDecision />} />
            <Route path="edit" element={<PlanEdit />} />
          </Route>

          <Route path="*" element={<NotFound />} />
        </Routes>
      </AppShell>
    </ToastProvider>
  )
}
