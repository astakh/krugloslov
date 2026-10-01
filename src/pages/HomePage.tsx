import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import apiClient from "../api/client";

interface DashboardData {
  profile: {
    level: string;
    dictionary: {
      id: number;
      name: string;
    };
  };
  today: string;
  lessons_today: number;
  daily_lesson_limit: number;
  resets_at: string;
  cta: "start" | "resume" | "limit_reached";
  resume: {
    lesson_id: number;
    exercises_done: number;
    exercises_total: number;
  } | null;
  words: {
    active: number;
    mastered: number;
    ignored: number;
  };
  streak: {
    current: number;
    longest: number;
    today_done: boolean;
  };
}

const HomePage: React.FC = () => {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { user, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    // Check if user is authenticated
    if (!isAuthenticated) {
      navigate("/auth");
      return;
    }
    
    loadDashboard();
  }, [isAuthenticated, navigate]);

  const loadDashboard = async () => {
    try {
      setLoading(true);
      const data = await apiClient.get<DashboardData>("/dashboard/summary");
      setDashboard(data);
      setError(null);
    } catch (err: any) {
      // Handle onboarding required error
      if (err?.error?.code === "onboarding_required") {
        navigate("/onboarding");
        return;
      }
      setError("Не удалось загрузить данные");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleCTA = () => {
    if (!dashboard) return;

    if (dashboard.cta === "start") {
      // Navigate to lesson preview
      navigate("/lesson/preview");
    } else if (dashboard.cta === "resume" && dashboard.resume) {
      // Navigate to resume page
      navigate(`/lesson/${dashboard.resume.lesson_id}/resume`);
    }
    // limit_reached doesn't have an action
  };

  const formatTimeUntilReset = () => {
    if (!dashboard) return "";

    const now = new Date();
    const resetTime = new Date(dashboard.resets_at);
    const diff = resetTime.getTime() - now.getTime();

    if (diff <= 0) return "скоро";

    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

    if (hours > 0) {
      return `${hours} ч ${minutes} мин`;
    }
    return `${minutes} мин`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-gray-500">Загрузка...</div>
      </div>
    );
  }

  if (error || !dashboard) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="text-red-500 mb-4">{error || "Ошибка загрузки"}</div>
          <button
            onClick={loadDashboard}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Повторить
          </button>
        </div>
      </div>
    );
  }

  const isStreakAtRisk = dashboard.streak.current > 0 && !dashboard.streak.today_done;

  return (
    <div className="max-w-2xl mx-auto p-4 space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg p-6 text-white">
        <h1 className="text-2xl font-bold mb-2">
          Привет{user?.email ? `, ${user.email.split('@')[0]}` : ''}! 👋
        </h1>
        <p className="text-blue-100">
          Уровень: {dashboard.profile.level} • {dashboard.profile.dictionary.name}
        </p>
      </div>

      {/* Streak Card */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Серия занятий</h2>
          <div className="flex items-center gap-2">
            <span className="text-3xl">
              {isStreakAtRisk ? "🔥" : dashboard.streak.current > 0 ? "🔥" : "⚪"}
            </span>
          </div>
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-3xl font-bold text-blue-600">
              {dashboard.streak.current}
            </div>
            <div className="text-sm text-gray-600">Текущая серия</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-purple-600">
              {dashboard.streak.longest}
            </div>
            <div className="text-sm text-gray-600">Рекорд</div>
          </div>
        </div>

        {isStreakAtRisk && (
          <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded">
            <p className="text-sm text-yellow-800">
              ⚠️ Позанимайтесь сегодня, чтобы сохранить серию!
            </p>
          </div>
        )}
      </div>

      {/* Lessons Today Card */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Уроки сегодня</h2>
        
        <div className="flex items-center justify-between mb-4">
          <div>
            <span className="text-3xl font-bold text-blue-600">
              {dashboard.lessons_today}
            </span>
            <span className="text-xl text-gray-400"> / {dashboard.daily_lesson_limit}</span>
          </div>
          <div className="text-sm text-gray-600">уроков начато</div>
        </div>

        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-blue-600 h-2 rounded-full transition-all"
            style={{
              width: `${Math.min(
                (dashboard.lessons_today / dashboard.daily_lesson_limit) * 100,
                100
              )}%`,
            }}
          />
        </div>
      </div>

      {/* Words Summary */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Слова</h2>
        
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">
              {dashboard.words.active}
            </div>
            <div className="text-sm text-gray-600">Изучаю</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">
              {dashboard.words.mastered}
            </div>
            <div className="text-sm text-gray-600">Выучено</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-600">
              {dashboard.words.ignored}
            </div>
            <div className="text-sm text-gray-600">Пропущено</div>
          </div>
        </div>
      </div>

      {/* CTA Button */}
      {dashboard.cta === "limit_reached" ? (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-center">
            <div className="text-5xl mb-4">🎉</div>
            <h2 className="text-xl font-bold mb-2">Лимит исчерпан</h2>
            <p className="text-gray-600 mb-4">
              Вы достигли дневного лимита уроков. Отличная работа!
            </p>
            <div className="text-sm text-gray-500">
              Лимит обновится через {formatTimeUntilReset()}
            </div>
            <button
              onClick={() => navigate("/profile")}
              className="mt-4 text-blue-600 hover:text-blue-700 text-sm"
            >
              Настройки обучения →
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={handleCTA}
          className="w-full bg-gradient-to-r from-blue-500 to-purple-600 text-white font-bold py-4 rounded-lg shadow-lg hover:shadow-xl transition-all transform hover:scale-[1.02]"
        >
          {dashboard.cta === "start" && "🚀 Начать урок"}
          {dashboard.cta === "resume" && dashboard.resume && (
            <>
              ▶️ Продолжить урок
              <div className="text-sm font-normal mt-1">
                {dashboard.resume.exercises_done} / {dashboard.resume.exercises_total} упражнений
              </div>
            </>
          )}
        </button>
      )}
    </div>
  );
};

export default HomePage;
