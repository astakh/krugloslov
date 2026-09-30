import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import apiClient from "../api/client";

interface HeatmapDay {
  date: string;
  count: number;
}

interface ProfileStats {
  current_streak: number;
  longest_streak: number;
  accuracy_30_days: number | null;
  accuracy_all_time: number | null;
  words_active: number;
  words_mastered: number;
  words_ignored: number;
  lessons_completed: number;
  heatmap: HeatmapDay[];
}

const ProfilePage: React.FC = () => {
  const [stats, setStats] = useState<ProfileStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.get<ProfileStats>("/profile/stats");
      setStats(data);
    } catch (err) {
      setError("Не удалось загрузить статистику");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    await logout();
  };

  const getHeatmapColor = (count: number) => {
    if (count === 0) return "bg-gray-100";
    if (count === 1) return "bg-green-200";
    if (count === 2) return "bg-green-300";
    if (count === 3) return "bg-green-400";
    return "bg-green-500";
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("ru-RU", { day: "numeric", month: "short" });
  };

  if (loading) {
    return (
      <div className="app-content py-8">
        <div className="text-center">
          <p className="text-gray-500">Загрузка...</p>
        </div>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="app-content py-8">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error || "Ошибка загрузки"}</p>
          <button
            onClick={loadStats}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
          >
            Повторить
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="app-content py-8">
      <h1 className="text-2xl font-bold mb-6">Профиль</h1>

      {/* User info */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold mb-2">{user?.email}</h2>
        <div className="flex gap-2">
          <button
            onClick={() => navigate("/settings")}
            className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
          >
            Настройки
          </button>
          <button
            onClick={() => navigate("/learning-profile")}
            className="px-4 py-2 bg-indigo-100 hover:bg-indigo-200 text-indigo-700 rounded-lg transition-colors"
          >
            Настройки обучения
          </button>
          <button
            onClick={handleLogout}
            className="px-4 py-2 bg-red-100 hover:bg-red-200 text-red-700 rounded-lg transition-colors"
          >
            Выйти
          </button>
        </div>
      </div>

      {/* Streak */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Серия занятий</h2>
        <div className="grid grid-cols-2 gap-4">
          <div className="text-center">
            <div className="text-3xl font-bold text-orange-600">
              {stats.current_streak}
            </div>
            <div className="text-sm text-gray-600">Текущая серия</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-purple-600">
              {stats.longest_streak}
            </div>
            <div className="text-sm text-gray-600">Рекорд</div>
          </div>
        </div>
      </div>

      {/* Accuracy */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Точность</h2>
        <div className="grid grid-cols-2 gap-4">
          <div className="text-center">
            <div className="text-3xl font-bold text-blue-600">
              {stats.accuracy_30_days !== null ? `${stats.accuracy_30_days}%` : "—"}
            </div>
            <div className="text-sm text-gray-600">За 30 дней</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-indigo-600">
              {stats.accuracy_all_time !== null ? `${stats.accuracy_all_time}%` : "—"}
            </div>
            <div className="text-sm text-gray-600">За всё время</div>
          </div>
        </div>
      </div>

      {/* Words */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Слова</h2>
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">
              {stats.words_active}
            </div>
            <div className="text-sm text-gray-600">Изучаю</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">
              {stats.words_mastered}
            </div>
            <div className="text-sm text-gray-600">Выучено</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-600">
              {stats.words_ignored}
            </div>
            <div className="text-sm text-gray-600">Игнор</div>
          </div>
        </div>
      </div>

      {/* Lessons */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Уроки</h2>
        <div className="text-center">
          <div className="text-3xl font-bold text-indigo-600">
            {stats.lessons_completed}
          </div>
          <div className="text-sm text-gray-600">Завершённых уроков</div>
        </div>
      </div>

      {/* Heatmap */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-lg font-semibold mb-4">Активность за год</h2>
        <div className="grid grid-cols-52 gap-1">
          {stats.heatmap.map((day, index) => (
            <div
              key={index}
              className={`w-2 h-2 rounded ${getHeatmapColor(day.count)}`}
              title={`${formatDate(day.date)}: ${day.count} ${day.count === 1 ? "урок" : "уроков"}`}
            />
          ))}
        </div>
        <div className="mt-4 flex items-center gap-2 text-xs text-gray-600">
          <span>Меньше</span>
          <div className="w-2 h-2 rounded bg-gray-100" />
          <div className="w-2 h-2 rounded bg-green-200" />
          <div className="w-2 h-2 rounded bg-green-300" />
          <div className="w-2 h-2 rounded bg-green-400" />
          <div className="w-2 h-2 rounded bg-green-500" />
          <span>Больше</span>
        </div>
      </div>
    </div>
  );
};

export default ProfilePage;
