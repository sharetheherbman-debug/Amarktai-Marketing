import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Toaster } from '@/components/ui/sonner';
import { Suspense, lazy, useEffect } from 'react';
import { Loader2 } from 'lucide-react';
import AuthProvider from '@/components/auth/AuthProvider';
import PwaInstallBanner from '@/components/ui/PwaInstallBanner';
import { useAuth } from '@/lib/auth';

// Lazy load pages
const LandingPage = lazy(() => import('@/app/page'));
const AboutPage = lazy(() => import('@/app/about/page'));
const PricingPage = lazy(() => import('@/app/pricing/page'));
const ContactPage = lazy(() => import('@/app/contact/page'));
const PrivacyPage = lazy(() => import('@/app/privacy/page'));
const TermsPage = lazy(() => import('@/app/terms/page'));
const LoginPage = lazy(() => import('@/app/login/page'));
const RegisterPage = lazy(() => import('@/app/register/page'));
const DashboardLayout = lazy(() => import('@/components/layout/DashboardLayout'));
const DashboardPage = lazy(() => import('@/app/dashboard/page'));
const WebAppsPage = lazy(() => import('@/app/webapps/page'));
const NewWebAppPage = lazy(() => import('@/app/webapps/new/page'));
const EditWebAppPage = lazy(() => import('@/app/webapps/edit/page'));
const BusinessDetailPage = lazy(() => import('@/app/businesses/detail/page'));
const ContentPage = lazy(() => import('@/app/content/page'));
const ApprovalPage = lazy(() => import('@/app/approval/page'));
const SchedulerPage = lazy(() => import('@/app/scheduler/page'));
const AnalyticsPage = lazy(() => import('@/app/analytics/page'));
const SettingsPage = lazy(() => import('@/app/settings/page'));
const IntegrationsPage = lazy(() => import('@/app/integrations/page'));
const EngagementPage = lazy(() => import('@/app/engagement/page'));
const AdminPage = lazy(() => import('@/app/admin/page'));
const ToolsPage = lazy(() => import('@/app/tools/page'));
const LeadsPage = lazy(() => import('@/app/leads/page'));
const GroupsPage = lazy(() => import('@/app/groups/page'));
const BlogPage = lazy(() => import('@/app/blog/page'));
const FeaturesPage = lazy(() => import('@/app/features/page'));
const ForgotPasswordPage = lazy(() => import('@/app/forgot-password/page'));
const ResetPasswordPage = lazy(() => import('@/app/reset-password/page'));
const VerifyEmailPage = lazy(() => import('@/app/verify-email/page'));

function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => { window.scrollTo(0, 0); }, [pathname]);
  return null;
}

function PageLoader() {
  return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: '#06070A' }}>
      <Loader2 className="w-8 h-8 animate-spin" style={{ color: '#2563FF' }} />
    </div>
  );
}

/** Redirect to /login when not authenticated; wait while auth is loading. */
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoaded } = useAuth();
  if (!isLoaded) return <PageLoader />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

/** Redirect authenticated users away from login/register. */
function PublicOnlyRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoaded } = useAuth();
  if (!isLoaded) return <PageLoader />;
  if (isAuthenticated) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

function AppRoutes() {
  const location = useLocation();
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes location={location}>
        <Route path="/" element={<LandingPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/pricing" element={<PricingPage />} />
        <Route path="/contact" element={<ContactPage />} />
        <Route path="/features" element={<FeaturesPage />} />
        <Route path="/privacy" element={<PrivacyPage />} />
        <Route path="/terms" element={<TermsPage />} />
        <Route path="/login" element={<PublicOnlyRoute><LoginPage /></PublicOnlyRoute>} />
        <Route path="/register" element={<PublicOnlyRoute><RegisterPage /></PublicOnlyRoute>} />
        <Route path="/forgot-password" element={<PublicOnlyRoute><ForgotPasswordPage /></PublicOnlyRoute>} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/verify-email" element={<VerifyEmailPage />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <DashboardLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="businesses" element={<WebAppsPage />} />
          <Route path="businesses/new" element={<NewWebAppPage />} />
          <Route path="businesses/:id" element={<BusinessDetailPage />} />
          <Route path="webapps" element={<Navigate to="/dashboard/businesses" replace />} />
          <Route path="webapps/new" element={<Navigate to="/dashboard/businesses/new" replace />} />
          <Route path="webapps/edit/:id" element={<EditWebAppPage />} />
          <Route path="webapps/:id" element={<BusinessDetailPage />} />
          <Route path="content" element={<ContentPage />} />
          <Route path="approval" element={<ApprovalPage />} />
          <Route path="scheduler" element={<SchedulerPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="integrations" element={<IntegrationsPage />} />
          <Route path="engagement" element={<EngagementPage />} />
          <Route path="tools" element={<ToolsPage />} />
          <Route path="leads" element={<LeadsPage />} />
          <Route path="groups" element={<GroupsPage />} />
          <Route path="blog" element={<BlogPage />} />
          <Route path="admin" element={<AdminPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <ScrollToTop />
        <AppRoutes />
        <Toaster position="top-right" richColors theme="dark" />
        <PwaInstallBanner />
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
