import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import apiClient from "../api/client";

interface VocabularyWord {
  word_id: number;
  lemma: string;
  pos: string;
  translations: string[];
  status: "active" | "mastered" | "ignored";
  stage: number;
  due_in_lessons: number;
}

interface VocabularyListResponse {
  words: VocabularyWord[];
  total: number;
  page: number;
  page_size: number;
}

type TabType = "all" | "active" | "mastered" | "ignored";

const DictionaryPage: React.FC = () => {
  const [words, setWords] = useState<VocabularyWord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchTimeout, setSearchTimeout] = useState<number | null>(null);
  
  const { user } = useAuth();
  const navigate = useNavigate();
  
  const pageSize = 20;

  useEffect(() => {
    loadWords();
  }, [activeTab, page, searchQuery]);

  const loadWords = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params = new URLSearchParams();
      params.append("page", page.toString());
      params.append("page_size", pageSize.toString());
      
      if (activeTab !== "all") {
        params.append("status", activeTab);
      }
      
      if (searchQuery.trim()) {
        params.append("q", searchQuery.trim());
      }
      
      const data = await apiClient.get<VocabularyListResponse>(
        `/vocabulary/list?${params.toString()}`
      );
      
      setWords(data.words);
      setTotal(data.total);
    } catch (err) {
      setError("Не удалось загрузить словарь");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (tab: TabType) => {
    setActiveTab(tab);
    setPage(1);
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchQuery(value);
    
    // Debounce search
    if (searchTimeout) {
      clearTimeout(searchTimeout);
    }
    
    const timeout = setTimeout(() => {
      setPage(1);
    }, 300);
    
    setSearchTimeout(timeout);
  };

  const handleStatusChange = async (wordId: number, newStatus: "active" | "ignored") => {
    try {
      await apiClient.patch(`/vocabulary/word/${wordId}/status`, {
        status: newStatus,
      });
      
      // Reload words
      await loadWords();
    } catch (err) {
      setError("Не удалось изменить статус слова");
      console.error(err);
    }
  };

  const handleWordClick = (wordId: number) => {
    navigate(`/vocabulary/word/${wordId}`);
  };

  const totalPages = Math.ceil(total / pageSize);

  const renderProgressBar = (stage: number) => {
    const percentage = (stage / 6) * 100;
    return (
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className="bg-indigo-600 h-2 rounded-full transition-all"
          style={{ width: `${percentage}%` }}
        />
      </div>
    );
  };

  const getStatusBadge = (status: string) => {
    const colors = {
      active: "bg-green-100 text-green-800",
      mastered: "bg-blue-100 text-blue-800",
      ignored: "bg-gray-100 text-gray-800",
    };
    
    const labels = {
      active: "Изучаю",
      mastered: "Выучено",
      ignored: "Игнор",
    };
    
    return (
      <span className={`px-2 py-1 text-xs font-medium rounded ${colors[status as keyof typeof colors]}`}>
        {labels[status as keyof typeof labels]}
      </span>
    );
  };

  return (
    <div className="app-content py-8">
      <h1 className="text-2xl font-bold mb-6">Мой словарь</h1>

      {/* Tabs */}
      <div className="flex gap-2 mb-4 border-b border-gray-200">
        <button
          onClick={() => handleTabChange("all")}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === "all"
              ? "text-indigo-600 border-b-2 border-indigo-600"
              : "text-gray-600 hover:text-gray-800"
          }`}
        >
          Все
        </button>
        <button
          onClick={() => handleTabChange("active")}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === "active"
              ? "text-indigo-600 border-b-2 border-indigo-600"
              : "text-gray-600 hover:text-gray-800"
          }`}
        >
          Изучаю
        </button>
        <button
          onClick={() => handleTabChange("mastered")}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === "mastered"
              ? "text-indigo-600 border-b-2 border-indigo-600"
              : "text-gray-600 hover:text-gray-800"
          }`}
        >
          Выучено
        </button>
        <button
          onClick={() => handleTabChange("ignored")}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === "ignored"
              ? "text-indigo-600 border-b-2 border-indigo-600"
              : "text-gray-600 hover:text-gray-800"
          }`}
        >
          Игнор
        </button>
      </div>

      {/* Search */}
      <div className="mb-6">
        <input
          type="text"
          placeholder="Поиск по слову или переводу..."
          value={searchQuery}
          onChange={handleSearchChange}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="text-center py-8">
          <p className="text-gray-500">Загрузка...</p>
        </div>
      )}

      {/* Words list */}
      {!loading && words.length === 0 && (
        <div className="text-center py-8">
          <p className="text-gray-500">Словарь пуст</p>
        </div>
      )}

      {!loading && words.length > 0 && (
        <>
          <div className="space-y-3">
            {words.map((word) => (
              <div
                key={word.word_id}
                onClick={() => handleWordClick(word.word_id)}
                className="p-4 bg-white rounded-lg border border-gray-200 hover:border-indigo-300 cursor-pointer transition-colors"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-lg font-medium">{word.lemma}</h3>
                      <span className="text-sm text-gray-500">({word.pos})</span>
                      {getStatusBadge(word.status)}
                    </div>
                    <p className="text-sm text-gray-600">
                      {word.translations.join(", ")}
                    </p>
                  </div>
                </div>

                {word.status === "active" && (
                  <div className="mt-3">
                    <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                      <span>Прогресс</span>
                      <span>
                        {word.stage}/6 • Повтор через {word.due_in_lessons}{" "}
                        {word.due_in_lessons === 1 ? "урок" : "уроков"}
                      </span>
                    </div>
                    {renderProgressBar(word.stage)}
                  </div>
                )}

                <div className="mt-3 flex gap-2">
                  {word.status === "active" && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleStatusChange(word.word_id, "ignored");
                      }}
                      className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 rounded transition-colors"
                    >
                      Не изучать
                    </button>
                  )}
                  {(word.status === "ignored" || word.status === "mastered") && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleStatusChange(word.word_id, "active");
                      }}
                      className="px-3 py-1 text-sm bg-indigo-100 hover:bg-indigo-200 text-indigo-700 rounded transition-colors"
                    >
                      Вернуть в изучение
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-6 flex items-center justify-center gap-2">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page === 1}
                className="px-3 py-1 border border-gray-300 rounded disabled:opacity-50 disabled:cursor-not-allowed"
              >
                ←
              </button>
              <span className="text-sm text-gray-600">
                {page} из {totalPages}
              </span>
              <button
                onClick={() => setPage(Math.min(totalPages, page + 1))}
                disabled={page === totalPages}
                className="px-3 py-1 border border-gray-300 rounded disabled:opacity-50 disabled:cursor-not-allowed"
              >
                →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default DictionaryPage;
