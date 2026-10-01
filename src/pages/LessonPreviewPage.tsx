import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import apiClient, { ApiError } from "../api/client";

interface WordInfo {
  word_id: number;
  lemma: string;
  pos: string;
  translations?: string[];
}

interface PreviewData {
  state: "ready" | "resume" | "limit_reached" | "no_words";
  lesson_number?: number;
  lesson_id?: number;
  exercises_done?: number;
  exercises_total?: number;
  resets_at?: string;
  due_words?: WordInfo[];
  new_words?: WordInfo[];
  dictionary_exhausted?: boolean;
}

const LessonPreviewPage: React.FC = () => {
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showLoader, setShowLoader] = useState(false);
  
  const { accessToken } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    loadPreview();
  }, []);

  const loadPreview = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.post<PreviewData>("/lesson/preview");
      setPreview(data);
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.error?.message || "Ошибка загрузки");
    } finally {
      setLoading(false);
    }
  };

  const handleDeclineWord = async (wordId: number) => {
    try {
      const response = await apiClient.post<{ preview: PreviewData }>(
        "/lesson/new-word/decline",
        { word_id: wordId }
      );
      setPreview(response.preview);
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.error?.message || "Ошибка отказа от слова");
    }
  };

  const handleStartLesson = async () => {
    if (!preview || preview.state !== "ready") return;

    setStarting(true);
    setShowLoader(true);
    setError(null);

    try {
      const wordIds = [
        ...(preview.due_words || []).map(w => w.word_id),
        ...(preview.new_words || []).map(w => w.word_id),
      ];

      // Generate idempotency key
      const idempotencyKey = `lesson_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

      const response = await fetch("/api/lesson/start", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${accessToken}`,
          "Idempotency-Key": idempotencyKey,
        },
        credentials: "include",
        body: JSON.stringify({ word_ids: wordIds }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw errorData;
      }

      const data = await response.json();
      
      // Navigate to first exercise
      navigate(`/lesson/${data.lesson_id}/exercise/${data.current_exercise.exercise_id}`);
    } catch (err) {
      const apiError = err as ApiError;
      
      if (apiError.error?.code === "llm_unavailable") {
        setError("Не удалось сгенерировать предложения. Попробуйте позже.");
      } else if (apiError.error?.code === "preview_outdated") {
        setError("Состав урока изменился. Обновите страницу.");
        await loadPreview();
      } else {
        setError(apiError.error?.message || "Ошибка создания урока");
      }
    } finally {
      setStarting(false);
      setShowLoader(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-500">Загрузка...</div>
      </div>
    );
  }

  if (showLoader) {
    return (
      <div className="fixed inset-0 bg-white flex items-center justify-center z-50">
        <div className="text-center">
          <div className="text-5xl mb-4 animate-pulse">📚</div>
          <div className="text-xl font-semibold text-gray-700">Готовим урок...</div>
        </div>
      </div>
    );
  }

  if (!preview || preview.state !== "ready") {
    return (
      <div className="max-w-2xl mx-auto p-4">
        <div className="bg-white rounded-lg shadow p-6 text-center">
          {preview?.state === "resume" && preview.lesson_id && (
            <>
              <div className="text-5xl mb-4">▶️</div>
              <h2 className="text-xl font-bold mb-2">Есть незавершённый урок</h2>
              <p className="text-gray-600 mb-4">
                Выполнено {preview.exercises_done} из {preview.exercises_total} упражнений
              </p>
              <button
                onClick={() => navigate(`/lesson/${preview.lesson_id}/resume`)}
                className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
              >
                Продолжить
              </button>
            </>
          )}
          {preview?.state === "limit_reached" && (
            <>
              <div className="text-5xl mb-4">🎉</div>
              <h2 className="text-xl font-bold mb-2">Лимит исчерпан</h2>
              <p className="text-gray-600">Вы достигли дневного лимита уроков</p>
            </>
          )}
          {preview?.state === "no_words" && (
            <>
              <div className="text-5xl mb-4">📭</div>
              <h2 className="text-xl font-bold mb-2">Нет слов для изучения</h2>
              <p className="text-gray-600">Добавьте слова в словарь</p>
            </>
          )}
          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto p-4 space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg p-6 text-white">
        <h1 className="text-2xl font-bold">Урок №{preview.lesson_number}</h1>
        <p className="text-blue-100 mt-1">Состав урока</p>
      </div>

      {/* Dictionary exhausted banner */}
      {preview.dictionary_exhausted && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-sm text-yellow-800">
            ⚠️ Слова в словаре заканчиваются, выберите другой словарь
          </p>
        </div>
      )}

      {/* Due words */}
      {preview.due_words && preview.due_words.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">
            Повторение ({preview.due_words.length} слов)
          </h2>
          <div className="space-y-2">
            {preview.due_words.map((word) => (
              <div
                key={word.word_id}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
              >
                <div>
                  <span className="font-medium">{word.lemma}</span>
                  <span className="text-sm text-gray-500 ml-2">({word.pos})</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* New words */}
      {preview.new_words && preview.new_words.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">
            Новые слова ({preview.new_words.length})
          </h2>
          <div className="space-y-2">
            {preview.new_words.map((word) => (
              <div
                key={word.word_id}
                className="flex items-center justify-between p-3 bg-blue-50 rounded-lg"
              >
                <div>
                  <div className="font-medium">{word.lemma}</div>
                  <div className="text-sm text-gray-600">
                    {word.translations?.join(", ")}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">({word.pos})</div>
                </div>
                <button
                  onClick={() => handleDeclineWord(word.word_id)}
                  disabled={starting}
                  className="text-red-500 hover:text-red-700 disabled:opacity-50 text-2xl leading-none"
                  title="Отказаться от слова"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-sm text-red-600 mb-3">{error}</p>
          <button
            onClick={loadPreview}
            className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 text-sm"
          >
            Повторить
          </button>
        </div>
      )}

      {/* Start button */}
      <button
        onClick={handleStartLesson}
        disabled={starting || !preview.due_words?.length && !preview.new_words?.length}
        className="w-full py-4 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-bold text-lg rounded-lg shadow-lg hover:shadow-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {starting ? "Создание урока..." : "🚀 Поехали!"}
      </button>
    </div>
  );
};

export default LessonPreviewPage;
