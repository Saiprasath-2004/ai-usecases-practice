import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppShell } from './components/layout/AppShell';
import { ToastProvider } from './components/Toast';
import { DashboardPage } from './pages/DashboardPage';
import { JobsListPage } from './pages/JobsListPage';
import { JobDetailPage } from './pages/JobDetailPage';
import { CandidatesPage } from './pages/CandidatesPage';
import { ApplicationDetailPage } from './pages/ApplicationDetailPage';
import { RecruiterReviewPage } from './pages/RecruiterReviewPage';
import { CalendarPage } from './pages/CalendarPage';
import { InterviewsPage } from './pages/InterviewsPage';
import { NotificationsPage } from './pages/NotificationsPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { SettingsPage } from './pages/SettingsPage';
import { QuickEvaluatePage } from './pages/QuickEvaluatePage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 10_000,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<AppShell />}>
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/jobs" element={<JobsListPage />} />
              <Route path="/jobs/:jobId" element={<JobDetailPage />} />
              <Route path="/jobs/:jobId/candidates" element={<JobDetailPage />} />
              <Route path="/candidates" element={<CandidatesPage />} />
              <Route path="/applications/:applicationId" element={<ApplicationDetailPage />} />
              <Route path="/human-review" element={<RecruiterReviewPage />} />
              <Route path="/calendar" element={<CalendarPage />} />
              <Route path="/interviews" element={<InterviewsPage />} />
              <Route path="/notifications" element={<NotificationsPage />} />
              <Route path="/analytics" element={<AnalyticsPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/quick-evaluate" element={<QuickEvaluatePage />} />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>
  );
}
