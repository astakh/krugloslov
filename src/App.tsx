import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "./contexts/AuthContext";
import BottomNav from "./components/BottomNav";
import HomePage from "./pages/HomePage";
import AuthPage from "./pages/AuthPage";
import OnboardingPage from "./pages/OnboardingPage";
import DictionaryPage from "./pages/DictionaryPage";
import ProfilePage from "./pages/ProfilePage";
import LessonPage from "./pages/LessonPage";
import LessonPreviewPage from "./pages/LessonPreviewPage";
import ExercisePage from "./pages/ExercisePage";
import ReviewPage from "./pages/ReviewPage";
import AdminPage from "./pages/AdminPage";

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
          <Route path="/" element={<HomePage />} />
          <Route path="/auth" element={<AuthPage />} />
          <Route path="/onboarding" element={<OnboardingPage />} />
          <Route path="/dictionary" element={<DictionaryPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/lesson/preview" element={<LessonPreviewPage />} />
          <Route path="/lesson/:lessonId/exercise/:exerciseId" element={<ExercisePage />} />
          <Route path="/lesson/:lessonId/review/:exerciseId" element={<ReviewPage />} />
          <Route path="/lesson/*" element={<LessonPage />} />
          <Route path="/admin" element={<AdminPage />} />
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
