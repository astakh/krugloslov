import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import apiClient, { ApiError } from "../api/client";

interface Dictionary {
  id: number;
  code: string;
  name: string;
  description: string;
  is_general: boolean;
}

interface ErrorDetail {
  index: number;
  lemma?: string;
  pos?: string;
  code: string;
  message: string;
}

interface ImportReport {
  dictionary: {
    code: string;
    name: string;
    created: boolean;
  };
  added: number;
  linked: number;
  skipped: number;
  errors: number;
  error_details: ErrorDetail[];
}

interface DryRunReport {
  dictionary: {
    code: string;
    name: string;
    created: boolean;
  };
  total_words: number;
  valid_words: number;
  skipped: number;
  errors: number;
  error_details: ErrorDetail[];
}

const AdminPage: React.FC = () => {
  const [dictionaries, setDictionaries] = useState<Dictionary[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [report, setReport] = useState<ImportReport | DryRunReport | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const { accessToken } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    // Load dictionaries
    loadDictionaries();
  }, []);

  const loadDictionaries = async () => {
    try {
      const data = await apiClient.get<Dictionary[]>("/admin/dictionaries");
      setDictionaries(data);
    } catch (err) {
      const apiError = err as ApiError;
      if (apiError.error?.code === "forbidden") {
        navigate("/");
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setReport(null);
      setError(null);
    }
  };

  const handleDryRun = async () => {
    if (!file) return;

    setIsLoading(true);
    setError(null);
    setReport(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch("/api/admin/dictionaries/import?dry_run=true", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw errorData;
      }

      const data = await response.json();
      setReport(data);
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.error?.message || "Ошибка при проверке файла");
    } finally {
      setIsLoading(false);
    }
  };

  const handleImport = async () => {
    if (!file) return;

    setIsLoading(true);
    setError(null);
    setReport(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch("/api/admin/dictionaries/import", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw errorData;
      }

      const data = await response.json();
      setReport(data);
      
      // Reload dictionaries
      await loadDictionaries();
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.error?.message || "Ошибка при импорте");
    } finally {
      setIsLoading(false);
    }
  };

  const isDryRunReport = (report: any): report is DryRunReport => {
    return "total_words" in report;
  };

  return (
    <div className="app-content py-8">
      <h1 className="text-2xl font-bold mb-6">Админка</h1>

      {/* Navigation */}
      <div className="flex gap-3 mb-6">
        <button
          onClick={() => navigate("/admin/reports")}
          className="px-4 py-2 bg-indigo-100 hover:bg-indigo-200 text-indigo-700 rounded-lg transition-colors"
        >
          Жалобы пользователей
        </button>
        <button
          onClick={() => navigate("/admin/users")}
          className="px-4 py-2 bg-indigo-100 hover:bg-indigo-200 text-indigo-700 rounded-lg transition-colors"
        >
          Пользователи
        </button>
        <button
          onClick={() => navigate("/admin/db")}
          className="px-4 py-2 bg-indigo-100 hover:bg-indigo-200 text-indigo-700 rounded-lg transition-colors"
        >
          База данных
        </button>
        <button
          onClick={() => navigate("/admin/prompts")}
          className="px-4 py-2 bg-indigo-100 hover:bg-indigo-200 text-indigo-700 rounded-lg transition-colors"
        >
          Промпты LLM
        </button>
      </div>

      {/* Dictionaries List */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-4">Словари</h2>
        {dictionaries.length === 0 ? (
          <p className="text-gray-500">Словари не найдены</p>
        ) : (
          <div className="space-y-2">
            {dictionaries.map((dict) => (
              <div
                key={dict.id}
                className="p-4 bg-white rounded-lg border border-gray-200"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium">{dict.name}</h3>
                    <p className="text-sm text-gray-500">
                      Код: {dict.code}
                      {dict.is_general && (
                        <span className="ml-2 px-2 py-1 bg-indigo-100 text-indigo-700 text-xs rounded">
                          Общий
                        </span>
                      )}
                    </p>
                    {dict.description && (
                      <p className="text-sm text-gray-600 mt-1">{dict.description}</p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Import Form */}
      <section>
        <h2 className="text-xl font-semibold mb-4">Импорт словаря</h2>
        
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              JSON файл
            </label>
            <input
              type="file"
              accept=".json"
              onChange={handleFileChange}
              className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
            />
          </div>

          <div className="flex gap-3">
            <button
              onClick={handleDryRun}
              disabled={!file || isLoading}
              className="px-4 py-2 bg-gray-600 hover:bg-gray-700 disabled:bg-gray-400 text-white font-medium rounded-lg transition-colors"
            >
              {isLoading ? "Проверка..." : "Проверить"}
            </button>
            <button
              onClick={handleImport}
              disabled={!file || isLoading}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white font-medium rounded-lg transition-colors"
            >
              {isLoading ? "Импорт..." : "Применить"}
            </button>
          </div>

          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}
        </div>
      </section>

      {/* Report */}
      {report && (
        <section className="mt-8">
          <h2 className="text-xl font-semibold mb-4">
            {isDryRunReport(report) ? "Результат проверки" : "Результат импорта"}
          </h2>

          <div className="bg-white p-6 rounded-lg border border-gray-200">
            <div className="mb-4">
              <h3 className="font-medium">
                Словарь: {report.dictionary.name} ({report.dictionary.code})
              </h3>
              <p className="text-sm text-gray-500">
                {report.dictionary.created ? "Создан новый" : "Использован существующий"}
              </p>
            </div>

            {isDryRunReport(report) ? (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-600">Всего слов</p>
                  <p className="text-2xl font-bold">{report.total_words}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Валидных</p>
                  <p className="text-2xl font-bold text-green-600">{report.valid_words}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Пропущено</p>
                  <p className="text-2xl font-bold text-yellow-600">{report.skipped}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Ошибок</p>
                  <p className="text-2xl font-bold text-red-600">{report.errors}</p>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-600">Добавлено слов</p>
                  <p className="text-2xl font-bold text-green-600">{report.added}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Связей создано</p>
                  <p className="text-2xl font-bold">{report.linked}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Пропущено</p>
                  <p className="text-2xl font-bold text-yellow-600">{report.skipped}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Ошибок</p>
                  <p className="text-2xl font-bold text-red-600">{report.errors}</p>
                </div>
              </div>
            )}

            {report.error_details.length > 0 && (
              <div className="mt-6">
                <h4 className="font-medium mb-2">
                  Ошибки (показано {Math.min(report.error_details.length, 200)} из {report.errors})
                </h4>
                <div className="max-h-64 overflow-y-auto border border-gray-200 rounded">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 sticky top-0">
                      <tr>
                        <th className="px-3 py-2 text-left">Индекс</th>
                        <th className="px-3 py-2 text-left">Слово</th>
                        <th className="px-3 py-2 text-left">Код</th>
                        <th className="px-3 py-2 text-left">Описание</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.error_details.map((err, idx) => (
                        <tr key={idx} className="border-t border-gray-200">
                          <td className="px-3 py-2">{err.index}</td>
                          <td className="px-3 py-2">
                            {err.lemma} {err.pos && `(${err.pos})`}
                          </td>
                          <td className="px-3 py-2 font-mono text-xs">{err.code}</td>
                          <td className="px-3 py-2">{err.message}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  );
};

export default AdminPage;
