import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import apiClient from "../api/client";

interface PromptListItem {
  key: string;
  updated_at: string | null;
  updated_by: number | null;
}

interface PromptDetail {
  key: string;
  system_template: string;
  required_placeholders: string[];
  updated_at: string | null;
  updated_by: number | null;
}

interface PromptHistoryItem {
  id: number;
  system_template: string;
  created_at: string;
  created_by: number | null;
}

interface PromptHistoryListResponse {
  items: PromptHistoryItem[];
  total: number;
  page: number;
  page_size: number;
}

const AdminPromptsPage: React.FC = () => {
  const [prompts, setPrompts] = useState<PromptListItem[]>([]);
  const [selectedPrompt, setSelectedPrompt] = useState<PromptDetail | null>(null);
  const [history, setHistory] = useState<PromptHistoryItem[]>([]);
  const [editing, setEditing] = useState(false);
  const [template, setTemplate] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [historyPage, setHistoryPage] = useState(1);
  const [historyTotal, setHistoryTotal] = useState(0);
  
  const navigate = useNavigate();

  useEffect(() => {
    loadPrompts();
  }, []);

  useEffect(() => {
    if (selectedPrompt) {
      loadHistory();
    }
  }, [selectedPrompt, historyPage]);

  const loadPrompts = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.get<PromptListItem[]>("/admin/prompts");
      setPrompts(data);
    } catch (err) {
      setError("Не удалось загрузить список промптов");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadPromptDetail = async (key: string) => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.get<PromptDetail>(`/admin/prompts/${key}`);
      setSelectedPrompt(data);
      setTemplate(data.system_template);
      setEditing(false);
      setHistoryPage(1);
    } catch (err) {
      setError("Не удалось загрузить промпт");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadHistory = async () => {
    if (!selectedPrompt) return;
    
    try {
      const data = await apiClient.get<PromptHistoryListResponse>(
        `/admin/prompts/${selectedPrompt.key}/history?page=${historyPage}&page_size=10`
      );
      setHistory(data.items);
      setHistoryTotal(data.total);
    } catch (err) {
      console.error("Failed to load history", err);
    }
  };

  const handleSave = async () => {
    if (!selectedPrompt) return;

    try {
      setLoading(true);
      setError(null);
      setSuccess(null);
      
      await apiClient.put(`/admin/prompts/${selectedPrompt.key}`, {
        system_template: template,
      });
      
      setSuccess("Промпт успешно сохранён");
      setEditing(false);
      await loadPromptDetail(selectedPrompt.key);
    } catch (err: any) {
      if (err.error) {
        setError(`${err.error.code}: ${err.error.message}`);
      } else {
        setError("Не удалось сохранить промпт");
      }
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleRollback = async (historyId: number) => {
    if (!selectedPrompt) return;
    
    if (!confirm("Вы уверены, что хотите откатить промпт к этой версии?")) {
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setSuccess(null);
      
      await apiClient.post(`/admin/prompts/${selectedPrompt.key}/rollback`, {
        history_id: historyId,
      });
      
      setSuccess("Промпт успешно откачен к предыдущей версии");
      await loadPromptDetail(selectedPrompt.key);
    } catch (err: any) {
      if (err.error) {
        setError(`${err.error.code}: ${err.error.message}`);
      } else {
        setError("Не удалось откатить промпт");
      }
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return "Никогда";
    return new Date(dateString).toLocaleString("ru-RU");
  };

  const historyTotalPages = Math.ceil(historyTotal / 10);

  return (
    <div className="app-content py-8">
      <button
        onClick={() => navigate("/admin")}
        className="mb-4 text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
      >
        ← Назад в админку
      </button>

      <h1 className="text-2xl font-bold mb-6">Промпты LLM</h1>

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

      {!selectedPrompt ? (
        // Prompts list
        <div>
          {loading ? (
            <div className="text-center py-8">
              <p className="text-gray-500">Загрузка...</p>
            </div>
          ) : (
            <div className="space-y-2">
              {prompts.map((prompt) => (
                <div
                  key={prompt.key}
                  onClick={() => loadPromptDetail(prompt.key)}
                  className="p-4 bg-white rounded-lg border border-gray-200 hover:border-indigo-300 cursor-pointer transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-medium text-gray-900">{prompt.key}</h3>
                      <p className="text-sm text-gray-500">
                        Обновлено: {formatDate(prompt.updated_at)}
                      </p>
                    </div>
                    <div className="text-sm text-gray-500">
                      {prompt.updated_by && `Автор: ${prompt.updated_by}`}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        // Prompt detail
        <div>
          <div className="mb-4 flex items-center justify-between">
            <button
              onClick={() => setSelectedPrompt(null)}
              className="text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
            >
              ← К списку промптов
            </button>
            <h2 className="text-xl font-bold">{selectedPrompt.key}</h2>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <p className="text-sm text-gray-600">
                  Обновлено: {formatDate(selectedPrompt.updated_at)}
                </p>
                {selectedPrompt.updated_by && (
                  <p className="text-sm text-gray-600">
                    Автор: {selectedPrompt.updated_by}
                  </p>
                )}
              </div>
              {!editing && (
                <button
                  onClick={() => setEditing(true)}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
                >
                  Редактировать
                </button>
              )}
            </div>

            {selectedPrompt.required_placeholders.length > 0 && (
              <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-sm text-blue-800">
                  <strong>Обязательные плейсхолдеры:</strong>{" "}
                  {selectedPrompt.required_placeholders.map((p) => `{${p}}`).join(", ")}
                </p>
              </div>
            )}

            {editing ? (
              <div>
                <textarea
                  value={template}
                  onChange={(e) => setTemplate(e.target.value)}
                  className="w-full h-96 px-4 py-2 border border-gray-300 rounded-lg font-mono text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="Введите шаблон промпта..."
                />
                <div className="mt-4 flex gap-2">
                  <button
                    onClick={handleSave}
                    disabled={loading}
                    className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
                  >
                    {loading ? "Сохранение..." : "Сохранить"}
                  </button>
                  <button
                    onClick={() => {
                      setEditing(false);
                      setTemplate(selectedPrompt.system_template);
                    }}
                    className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
                  >
                    Отмена
                  </button>
                </div>
              </div>
            ) : (
              <pre className="p-4 bg-gray-50 rounded-lg overflow-x-auto text-sm">
                {selectedPrompt.system_template}
              </pre>
            )}
          </div>

          {/* History */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h3 className="text-lg font-semibold mb-4">История изменений</h3>
            
            {history.length === 0 ? (
              <p className="text-gray-500 text-center py-4">История пуста</p>
            ) : (
              <div className="space-y-3">
                {history.map((item) => (
                  <div
                    key={item.id}
                    className="p-4 border border-gray-200 rounded-lg"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <p className="text-sm text-gray-600">
                          Версия #{item.id} • {formatDate(item.created_at)}
                        </p>
                        {item.created_by && (
                          <p className="text-xs text-gray-500">
                            Автор: {item.created_by}
                          </p>
                        )}
                      </div>
                      <button
                        onClick={() => handleRollback(item.id)}
                        className="px-3 py-1 text-sm bg-yellow-100 text-yellow-700 rounded hover:bg-yellow-200"
                      >
                        Откатить
                      </button>
                    </div>
                    <pre className="p-2 bg-gray-50 rounded text-xs overflow-x-auto max-h-32">
                      {item.system_template}
                    </pre>
                  </div>
                ))}
              </div>
            )}

            {/* Pagination */}
            {historyTotalPages > 1 && (
              <div className="mt-4 flex items-center justify-center gap-2">
                <button
                  onClick={() => setHistoryPage(Math.max(1, historyPage - 1))}
                  disabled={historyPage === 1}
                  className="px-3 py-1 border border-gray-300 rounded disabled:opacity-50"
                >
                  ←
                </button>
                <span className="text-sm text-gray-600">
                  {historyPage} из {historyTotalPages}
                </span>
                <button
                  onClick={() => setHistoryPage(Math.min(historyTotalPages, historyPage + 1))}
                  disabled={historyPage === historyTotalPages}
                  className="px-3 py-1 border border-gray-300 rounded disabled:opacity-50"
                >
                  →
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminPromptsPage;
