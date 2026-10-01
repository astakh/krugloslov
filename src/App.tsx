import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "./contexts/AuthContext";
import BottomNav from "./components/BottomNav";
import ProtectedRoute from "./components/ProtectedRoute";
import HomePage from "./pages/HomePage";
import AuthPage from "./pages/AuthPage";
import OnboardingPage from "./pages/OnboardingPage";
import DictionaryPage from "./pages/DictionaryPage";
import ProfilePage from "./pages/ProfilePage";
import LessonPage from "./pages/LessonPage";
import LessonPreviewPage from "./pages/LessonPreviewPage";
import ExercisePage from "./pages/ExercisePage";
import ReviewPage from "./pages/ReviewPage";
import ResumePage from "./pages/ResumePage";
import LessonCompletePage from "./pages/LessonCompletePage";
import WordDetailPage from "./pages/WordDetailPage";
import SettingsPage from "./pages/SettingsPage";
import LearningProfilePage from "./pages/LearningProfilePage";
import AdminPage from "./pages/AdminPage";
import AdminReportsPage from "./pages/AdminReportsPage";
import AdminUsersPage from "./pages/AdminUsersPage";
import AdminDbPage from "./pages/AdminDbPage";
import AdminPromptsPage from "./pages/AdminPromptsPage";

// TanStack Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
  },
});

const AppContent: React.FC = () => {
  return (
    <div className="page-wrapper">
      <main className="page-content">
        <Routes>
          {/* Public routes */}
          <Route path="/auth" element={<AuthPage />} />
          
          {/* Protected routes - redirect to /auth if not authenticated */}
          <Route path="/" element={<ProtectedRoute><HomePage /></ProtectedRoute>} />
          <Route path="/onboarding" element={<ProtectedRoute><OnboardingPage /></ProtectedRoute>} />
          <Route path="/dictionary" element={<ProtectedRoute><DictionaryPage /></ProtectedRoute>} />
          <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
          <Route path="/vocabulary/word/:wordId" element={<ProtectedRoute><WordDetailPage /></ProtectedRoute>} />
          <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
          <Route path="/learning-profile" element={<ProtectedRoute><LearningProfilePage /></ProtectedRoute>} />
          <Route path="/admin" element={<ProtectedRoute><AdminPage /></ProtectedRoute>} />
          <Route path="/admin/reports" element={<ProtectedRoute><AdminReportsPage /></ProtectedRoute>} />
          <Route path="/admin/users" element={<ProtectedRoute><AdminUsersPage /></ProtectedRoute>} />
          <Route path="/admin/db" element={<ProtectedRoute><AdminDbPage /></ProtectedRoute>} />
          <Route path="/admin/prompts" element={<ProtectedRoute><AdminPromptsPage /></ProtectedRoute>} />
          
          {/* Lesson routes - specific routes first */}
          <Route path="/lesson/preview" element={<ProtectedRoute><LessonPreviewPage /></ProtectedRoute>} />
          <Route path="/lesson/:lessonId/exercise/:exerciseId" element={<ProtectedRoute><ExercisePage /></ProtectedRoute>} />
          <Route path="/lesson/:lessonId/review/:exerciseId" element={<ProtectedRoute><ReviewPage /></ProtectedRoute>} />
          <Route path="/lesson/:lessonId/resume" element={<ProtectedRoute><ResumePage /></ProtectedRoute>} />
          <Route path="/lesson/:lessonId/complete" element={<ProtectedRoute><LessonCompletePage /></ProtectedRoute>} />
          <Route path="/lesson/:lessonId/summary" element={<ProtectedRoute><LessonCompletePage /></ProtectedRoute>} />
          
          {/* Catch-all for lesson - must be last */}
          <Route path="/lesson/*" element={<ProtectedRoute><LessonPage /></ProtectedRoute>} />
        </Routes>
      </main>
      <BottomNav />
    </div>
  );
};

const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <AppContent />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

export default App;
