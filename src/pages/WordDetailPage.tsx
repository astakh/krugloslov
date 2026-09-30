import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import apiClient from "../api/client";

interface ContextHistoryItem {
  sentence: string;
  surface_form: string | null;
  result: "correct" | "typo" | "incorrect" | null;
  date: string;
}

interface WordDetail {
  word_id: number;
  lemma: string;
  pos: string;
  translations: string[];
  status: "active" | "mastered" | "ignored";
  stage: number;
  due_in_lessons: number;
  context_history: ContextHistoryItem[];
}

const WordDetailPage: React.FC = () => {
  const { wordId } = useParams<{ wordId: string }>();
  const navigate = useNavigate();
  const [word, setWord] = useState<WordDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadWordDetail();
  }, [wordId]);

  const loadWordDetail = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.get<WordDetail>(`/vocabulary/word/${wordId}`);
      setWord(data);
    } catch (err) {
      setError("Не удалось загрузить информацию о слове");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleStatusChange = async (newStatus: "active" | "ignored") => {
    try {
      await apiClient.patch(`/vocabulary/word/${wordId}/status`, {
        status: newStatus,
      });
      await loadWordDetail();
    } catch (err) {
      setError("Не удалось изменить статус слова");
      console.error(err);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("ru-RU", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  };

  const getResultColor = (result: string | null) => {
    if (!result) return "text-gray-500";
    switch (result) {
      case "correct":
        return "text-green-600";
      case "typo":
        return "text-yellow-600";
      case "incorrect":
        return "text-red-600";
      default:
        return "text-gray-500";
    }
  };

  const getResultLabel = (result: string | null) => {
    if (!result) return "Подсказка";
    switch (result) {
      case "correct":
        return "✓ Верно";
      case "typo":
        return "~ Опечатка";
      case "incorrect":
        return "✗ Неверно";
      default:
        return "";
    }
  };

  const highlightSurfaceForm = (sentence: string, surfaceForm: string | null) => {
    if (!surfaceForm) return sentence;
    
    const regex = new RegExp(`\\b${surfaceForm}\\b`, "gi");
    const parts = sentence.split(regex);
    const matches = sentence.match(regex);
    
    if (!matches) return sentence;
    
    const result: React.ReactNode[] = [];
    parts.forEach((part, index) => {
      result.push(part);
      if (index < matches.length) {
        result.push(
          <span key={index} className="font-bold text-indigo-600">
            {matches[index]}
          </span>
        );
      }
    });
    
    return result;
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

  if (error || !word) {
    return (
      <div className="app-content py-8">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error || "Слово не найдено"}</p>
          <button
            onClick={() => navigate("/dictionary")}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
          >
            Вернуться к словарю
          </button>
        </div>
      </div>
    );
  }

  const progressPercentage = (word.stage / 6) * 100;

  return (
    <div className="app-content py-8">
      {/* Back button */}
      <button
        onClick={() => navigate("/dictionary")}
        className="mb-4 text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
      >
        ← Назад к словарю
      </button>

      {/* Word info */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold mb-2">{word.lemma}</h1>
            <p className="text-gray-600">
              {word.pos} •{" "}
              {word.status === "active"
                ? "Изучаю"
                : word.status === "mastered"
                ? "Выучено"
                : "Игнор"}
            </p>
          </div>
        </div>

        {/* Translations */}
        <div className="mb-4">
          <h2 className="text-sm font-medium text-gray-500 mb-2">Переводы</h2>
          <p className="text-lg">{word.translations.join(", ")}</p>
        </div>

        {/* Progress */}
        {word.status === "active" && (
          <div className="mb-4">
            <div className="flex items-center justify-between text-sm text-gray-600 mb-2">
              <span>Прогресс изучения</span>
              <span>
                {word.stage}/6 • Повтор через {word.due_in_lessons}{" "}
                {word.due_in_lessons === 1 ? "урок" : "уроков"}
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-3">
              <div
                className="bg-indigo-600 h-3 rounded-full transition-all"
                style={{ width: `${progressPercentage}%` }}
              />
            </div>
          </div>
        )}

        {/* Status change buttons */}
        <div className="flex gap-2">
          {word.status === "active" && (
            <button
              onClick={() => handleStatusChange("ignored")}
              className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
            >
              Не изучать
            </button>
          )}
          {(word.status === "ignored" || word.status === "mastered") && (
            <button
              onClick={() => handleStatusChange("active")}
              className="px-4 py-2 bg-indigo-100 hover:bg-indigo-200 text-indigo-700 rounded-lg transition-colors"
            >
              Вернуть в изучение
            </button>
          )}
        </div>
      </div>

      {/* Context history */}
      {word.context_history.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-xl font-bold mb-4">История использования</h2>
          <div className="space-y-4">
            {word.context_history.map((item, index) => (
              <div
                key={index}
                className="p-4 bg-gray-50 rounded-lg border border-gray-200"
              >
                <div className="flex items-start justify-between mb-2">
                  <p className="text-lg flex-1">
                    {item.surface_form
                      ? highlightSurfaceForm(item.sentence, item.surface_form)
                      : item.sentence}
                  </p>
                  <span
                    className={`text-sm font-medium ml-2 ${getResultColor(
                      item.result
                    )}`}
                  >
                    {getResultLabel(item.result)}
                  </span>
                </div>
                <p className="text-sm text-gray-500">{formatDate(item.date)}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {word.context_history.length === 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6 text-center">
          <p className="text-gray-500">История использования пуста</p>
        </div>
      )}
    </div>
  );
};

export default WordDetailPage;
