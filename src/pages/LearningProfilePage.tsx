import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import apiClient from "../api/client";

interface Dictionary {
  id: number;
  code: string;
  name: string;
  description: string;
  is_general: boolean;
  words_total: number;
}

interface LearningProfile {
  level: string;
  dictionary_id: number;
  dictionary_name: string;
  daily_lesson_limit: number;
  daily_lesson_limit_max: number;
  words_per_lesson: number;
  words_per_lesson_max: number;
  stats: {
    words: {
      active: number;
      mastered: number;
      ignored: number;
    };
    accuracy_30_days: number | null;
    accuracy_all_time: number | null;
    lessons_completed: number;
  };
}

const LEVELS = ["A1", "A2", "B1", "B2"];

const LearningProfilePage: React.FC = () => {
  const [profile, setProfile] = useState<LearningProfile | null>(null);
  const [dictionaries, setDictionaries] = useState<Dictionary[]>([]);
  const [level, setLevel] = useState("A1");
  const [dictionaryId, setDictionaryId] = useState<number>(1);
  const [dailyLimit, setDailyLimit] = useState(5);
  const [wordsPerLesson, setWordsPerLesson] = useState(10);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  const navigate = useNavigate();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [profileData, dictionariesData] = await Promise.all([
        apiClient.get<LearningProfile>("/learning-profile"),
        apiClient.get<{ dictionaries: Dictionary[] }>("/dictionaries"),
      ]);
      
      setProfile(profileData);
      setLevel(profileData.level);
      setDictionaryId(profileData.dictionary_id);
      setDailyLimit(profileData.daily_lesson_limit);
      setWordsPerLesson(profileData.words_per_lesson);
      setDictionaries(dictionariesData.dictionaries);
    } catch (err) {
      setError("Не удалось загрузить данные");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await apiClient.patch("/learning-profile", {
        level,
        dictionary_id: dictionaryId,
        daily_lesson_limit: dailyLimit,
        words_per_lesson: wordsPerLesson,
      });
      
      setSuccess("Настройки успешно сохранены");
      
      // Reload data
      await loadData();
    } catch (err: any) {
      setError(err.error?.message || "Ошибка сохранения настроек");
    } finally {
      setSaving(false);
    }
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

  if (!profile) {
    return (
      <div className="app-content py-8">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error || "Ошибка загрузки"}</p>
          <button
            onClick={loadData}
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
      <button
        onClick={() => navigate("/settings")}
        className="mb-4 text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
      >
        ← Назад к настройкам
      </button>

      <h1 className="text-2xl font-bold mb-6">Настройки обучения</h1>

      {/* Level */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Уровень</h2>
        <div className="grid grid-cols-4 gap-2">
          {LEVELS.map((lvl) => (
            <button
              key={lvl}
              onClick={() => setLevel(lvl)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                level === lvl
                  ? "bg-indigo-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              {lvl}
            </button>
          ))}
        </div>
        <p className="text-sm text-gray-600 mt-2">
          Влияет на подбор новых слов и уровень генерации в следующих уроках
        </p>
      </div>

      {/* Dictionary */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Словарь</h2>
        <div className="space-y-2">
          {dictionaries.map((dict) => (
            <button
              key={dict.id}
              onClick={() => setDictionaryId(dict.id)}
              className={`w-full p-4 rounded-lg text-left transition-colors ${
                dictionaryId === dict.id
                  ? "bg-indigo-50 border-2 border-indigo-600"
                  : "bg-gray-50 border-2 border-transparent hover:bg-gray-100"
              }`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium">{dict.name}</div>
                  <div className="text-sm text-gray-600">{dict.description}</div>
                </div>
                <div className="text-sm text-gray-500">
                  {dict.words_total} слов
                  {dict.is_general && (
                    <span className="ml-2 px-2 py-1 bg-indigo-100 text-indigo-700 text-xs rounded">
                      Общий
                    </span>
                  )}
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Daily limit */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Дневной лимит уроков</h2>
        <div className="flex items-center gap-4">
          <input
            type="range"
            min="1"
            max={profile.daily_lesson_limit_max}
            value={dailyLimit}
            onChange={(e) => setDailyLimit(Number(e.target.value))}
            className="flex-1"
          />
          <div className="text-2xl font-bold text-indigo-600 w-12 text-center">
            {dailyLimit}
          </div>
        </div>
        <p className="text-sm text-gray-600 mt-2">
          От 1 до {profile.daily_lesson_limit_max} уроков в день
        </p>
      </div>

      {/* Words per lesson */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Количество слов в уроке</h2>
        <div className="flex items-center gap-4">
          <input
            type="range"
            min="5"
            max={profile.words_per_lesson_max}
            value={wordsPerLesson}
            onChange={(e) => setWordsPerLesson(Number(e.target.value))}
            className="flex-1"
          />
          <div className="text-2xl font-bold text-indigo-600 w-12 text-center">
            {wordsPerLesson}
          </div>
        </div>
        <p className="text-sm text-gray-600 mt-2">
          От 5 до {profile.words_per_lesson_max} слов в одном уроке
        </p>
      </div>

      {/* Statistics */}

      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Статистика обучения</h2>
        
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">
              {profile.stats.words.active}
            </div>
            <div className="text-sm text-gray-600">Изучаю</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">
              {profile.stats.words.mastered}
            </div>
            <div className="text-sm text-gray-600">Выучено</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-600">
              {profile.stats.words.ignored}
            </div>
            <div className="text-sm text-gray-600">Игнор</div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">
              {profile.stats.accuracy_30_days !== null
                ? `${profile.stats.accuracy_30_days}%`
                : "—"}
            </div>
            <div className="text-sm text-gray-600">Точность за 30 дней</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-indigo-600">
              {profile.stats.accuracy_all_time !== null
                ? `${profile.stats.accuracy_all_time}%`
                : "—"}
            </div>
            <div className="text-sm text-gray-600">Точность за всё время</div>
          </div>
        </div>

        <div className="text-center">
          <div className="text-2xl font-bold text-indigo-600">
            {profile.stats.lessons_completed}
          </div>
          <div className="text-sm text-gray-600">Завершённых уроков</div>
        </div>
      </div>

      {/* Error/Success */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {success && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-sm text-green-600">{success}</p>
        </div>
      )}

      {/* Save button */}
      <button
        onClick={handleSave}
        disabled={saving}
        className="w-full px-4 py-3 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white font-medium rounded-lg transition-colors"
      >
        {saving ? "Сохранение..." : "Сохранить"}
      </button>
    </div>
  );
};

export default LearningProfilePage;
