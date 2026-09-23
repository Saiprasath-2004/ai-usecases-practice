import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import AppShell from './components/AppShell';
import { ToastProvider } from './components/Toast';
import JobsListPage from './pages/JobsListPage';
import JobDetailPage from './pages/JobDetailPage';
import ApplicationDetailPanel from './components/ApplicationDetailPanel';
import QuickEvaluatePage from './pages/QuickEvaluatePage';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<AppShell />}>
              <Route path="/" element={<JobsListPage />} />
              <Route path="/jobs/:jobId" element={<JobDetailPage />}>
                <Route path="applications/:appId" element={<ApplicationDetailPanel />} />
              </Route>
              <Route path="/quick-evaluate" element={<QuickEvaluatePage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>
  );
}
