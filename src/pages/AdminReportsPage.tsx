import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import apiClient from "../api/client";

interface TargetWord {
  word_id: number;
  lemma: string;
  pos: string;
  surface_form?: string;
}

interface Report {
  id: number;
  user_id: number;
  user_email: string;
  exercise_id: number;
  target_sentence: string;
  reference_translation: string;
  user_translation?: string;
  target_words: TargetWord[];
  reason: string;
  comment: string;
  status: string;
  admin_note?: string;
  created_at: string;
  llm_call_ids: number[];
}

interface ReportsListResponse {
  reports: Report[];
  total: number;
  page: number;
  page_size: number;
}

const AdminReportsPage: React.FC = () => {
  const [reports, setReports] = useState<Report[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [adminNote, setAdminNote] = useState("");
  const [processing, setProcessing] = useState(false);
  
  const pageSize = 20;
  const navigate = useNavigate();

  useEffect(() => {
    loadReports();
  }, [page, statusFilter]);

  const loadReports = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params = new URLSearchParams();
      params.append("page", page.toString());
      params.append("page_size", pageSize.toString());
      
      if (statusFilter) {
        params.append("status", statusFilter);
      }
      
      const data = await apiClient.get<ReportsListResponse>(
        `/admin/reports?${params.toString()}`
      );
      
      setReports(data.reports);
      setTotal(data.total);
    } catch (err) {
      setError("Не удалось загрузить жалобы");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleProcess = async () => {
    if (!selectedReport) return;

    setProcessing(true);
    try {
      await apiClient.patch(`/admin/reports/${selectedReport.id}`, {
        status: "processed",
        admin_note: adminNote,
      });
      
      // Reload reports
      await loadReports();
      setSelectedReport(null);
      setAdminNote("");
    } catch (err) {
      setError("Не удалось обработать жалобу");
      console.error(err);
    } finally {
      setProcessing(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString("ru-RU");
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="app-content py-8">
      <h1 className="text-2xl font-bold mb-6">Жалобы пользователей</h1>

      {/* Filters */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-6">
        <div className="flex gap-4">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Статус
            </label>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            >
              <option value="">Все</option>
              <option value="new">Новые</option>
              <option value="processed">Обработанные</option>
            </select>
          </div>
        </div>
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

      {/* Reports list */}
      {!loading && reports.length === 0 && (
        <div className="text-center py-8">
          <p className="text-gray-500">Жалоб не найдено</p>
        </div>
      )}

      {!loading && reports.length > 0 && (
        <>
          <div className="space-y-3">
            {reports.map((report) => (
              <div
                key={report.id}
                className="bg-white rounded-lg border border-gray-200 p-4 hover:border-indigo-300 cursor-pointer transition-colors"
                onClick={() => {
                  setSelectedReport(report);
                  setAdminNote(report.admin_note || "");
                }}
              >
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm text-gray-500">
                        #{report.id} • {report.user_email}
                      </span>
                      <span
                        className={`px-2 py-1 text-xs font-medium rounded ${
                          report.status === "new"
                            ? "bg-yellow-100 text-yellow-800"
                            : "bg-green-100 text-green-800"
                        }`}
                      >
                        {report.status === "new" ? "Новая" : "Обработана"}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600">
                      Причина: <strong>{report.reason}</strong>
                    </p>
                    {report.comment && (
                      <p className="text-sm text-gray-600 mt-1">
                        {report.comment}
                      </p>
                    )}
                  </div>
                  <div className="text-xs text-gray-500">
                    {formatDate(report.created_at)}
                  </div>
                </div>

                <div className="mt-2 p-2 bg-gray-50 rounded">
                  <p className="text-sm text-gray-700">
                    {report.target_sentence}
                  </p>
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
                className="px-3 py-1 border border-gray-300 rounded disabled:opacity-50"
              >
                ←
              </button>
              <span className="text-sm text-gray-600">
                {page} из {totalPages}
              </span>
              <button
                onClick={() => setPage(Math.min(totalPages, page + 1))}
                disabled={page === totalPages}
                className="px-3 py-1 border border-gray-300 rounded disabled:opacity-50"
              >
                →
              </button>
            </div>
          )}
        </>
      )}

      {/* Report detail modal */}
      {selectedReport && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-start justify-between mb-4">
                <h2 className="text-xl font-bold">Жалоба #{selectedReport.id}</h2>
                <button
                  onClick={() => setSelectedReport(null)}
                  className="text-gray-400 hover:text-gray-600 text-2xl"
                >
                  ×
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Пользователь
                  </label>
                  <p className="text-gray-900">{selectedReport.user_email}</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Предложение
                  </label>
                  <p className="text-gray-900 p-2 bg-gray-50 rounded">
                    {selectedReport.target_sentence}
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Эталонный перевод
                  </label>
                  <p className="text-gray-900 p-2 bg-gray-50 rounded">
                    {selectedReport.reference_translation}
                  </p>
                </div>

                {selectedReport.user_translation && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Перевод пользователя
                    </label>
                    <p className="text-gray-900 p-2 bg-gray-50 rounded">
                      {selectedReport.user_translation}
                    </p>
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Целевые слова
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {selectedReport.target_words.map((word) => (
                      <span
                        key={word.word_id}
                        className="px-2 py-1 bg-indigo-100 text-indigo-700 text-sm rounded"
                      >
                        {word.lemma} ({word.pos})
                        {word.surface_form && ` → ${word.surface_form}`}
                      </span>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Причина
                  </label>
                  <p className="text-gray-900">{selectedReport.reason}</p>
                </div>

                {selectedReport.comment && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Комментарий
                    </label>
                    <p className="text-gray-900">{selectedReport.comment}</p>
                  </div>
                )}

                {selectedReport.llm_call_ids.length > 0 && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Связанные LLM вызовы
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {selectedReport.llm_call_ids.map((id) => (
                        <span
                          key={id}
                          className="px-2 py-1 bg-gray-100 text-gray-700 text-sm rounded"
                        >
                          #{id}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {selectedReport.status === "new" && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Заметка администратора
                    </label>
                    <textarea
                      value={adminNote}
                      onChange={(e) => setAdminNote(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      rows={3}
                      placeholder="Добавьте заметку..."
                    />
                  </div>
                )}

                {selectedReport.status === "processed" && selectedReport.admin_note && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Заметка администратора
                    </label>
                    <p className="text-gray-900 p-2 bg-gray-50 rounded">
                      {selectedReport.admin_note}
                    </p>
                  </div>
                )}

                {selectedReport.status === "new" && (
                  <button
                    onClick={handleProcess}
                    disabled={processing}
                    className="w-full px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white rounded-lg"
                  >
                    {processing ? "Обработка..." : "Обработать"}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminReportsPage;
