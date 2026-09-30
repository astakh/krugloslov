import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import apiClient from "../api/client";

interface TableInfo {
  table_name: string;
  row_count_estimate: number;
  columns_count: number;
}

interface ColumnInfo {
  name: string;
  type: string;
  is_primary_key: boolean;
  masked: boolean;
}

interface TableDataResponse {
  table_name: string;
  columns: ColumnInfo[];
  rows: Record<string, any>[];
  page: number;
  page_size: number;
  total: number | null;
}

const AdminDbPage: React.FC = () => {
  const [tables, setTables] = useState<TableInfo[]>([]);
  const [selectedTable, setSelectedTable] = useState<string | null>(null);
  const [tableData, setTableData] = useState<TableDataResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(25);
  const [orderBy, setOrderBy] = useState<string | null>(null);
  const [orderDir, setOrderDir] = useState<"asc" | "desc">("asc");
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [expandedCells, setExpandedCells] = useState<Set<string>>(new Set());
  
  const navigate = useNavigate();

  useEffect(() => {
    loadTables();
  }, []);

  useEffect(() => {
    if (selectedTable) {
      loadTableData();
    }
  }, [selectedTable, page, orderBy, orderDir, search]);

  const loadTables = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.get<TableInfo[]>("/admin/db/tables");
      setTables(data);
    } catch (err) {
      setError("Не удалось загрузить список таблиц");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadTableData = async () => {
    if (!selectedTable) return;

    try {
      setLoading(true);
      setError(null);
      
      const params = new URLSearchParams();
      params.append("page", page.toString());
      params.append("page_size", pageSize.toString());
      
      if (orderBy) {
        params.append("order_by", orderBy);
        params.append("order_dir", orderDir);
      }
      
      if (search) {
        params.append("search", search);
      }
      
      const data = await apiClient.get<TableDataResponse>(
        `/admin/db/tables/${selectedTable}?${params.toString()}`
      );
      
      setTableData(data);
    } catch (err: any) {
      if (err.error?.code === "table_not_found") {
        setError("Таблица не найдена");
      } else if (err.error?.code === "invalid_order_by") {
        setError("Неверный столбец для сортировки");
      } else {
        setError("Не удалось загрузить данные таблицы");
      }
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleTableClick = (tableName: string) => {
    setSelectedTable(tableName);
    setPage(1);
    setOrderBy(null);
    setOrderDir("asc");
    setSearch("");
    setSearchInput("");
  };

  const handleSort = (columnName: string) => {
    if (orderBy === columnName) {
      setOrderDir(orderDir === "asc" ? "desc" : "asc");
    } else {
      setOrderBy(columnName);
      setOrderDir("asc");
    }
    setPage(1);
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearch(searchInput);
    setPage(1);
  };

  const handleBack = () => {
    setSelectedTable(null);
    setTableData(null);
  };

  const toggleCellExpansion = (key: string) => {
    const newExpanded = new Set(expandedCells);
    if (newExpanded.has(key)) {
      newExpanded.delete(key);
    } else {
      newExpanded.add(key);
    }
    setExpandedCells(newExpanded);
  };

  const formatCellValue = (value: any, column: ColumnInfo, rowIndex: number) => {
    if (value === null || value === undefined) {
      return <span className="text-gray-400 italic">NULL</span>;
    }

    if (column.masked) {
      return <span className="text-gray-500">••••••••</span>;
    }

    const stringValue = typeof value === "object" ? JSON.stringify(value, null, 2) : String(value);
    const cellKey = `${rowIndex}-${column.name}`;
    const isExpanded = expandedCells.has(cellKey);

    if (stringValue.length > 50 && !isExpanded) {
      return (
        <div>
          <span className="text-gray-700">{stringValue.substring(0, 50)}...</span>
          <button
            onClick={() => toggleCellExpansion(cellKey)}
            className="ml-2 text-xs text-indigo-600 hover:text-indigo-700"
          >
            Показать
          </button>
        </div>
      );
    }

    if (stringValue.length > 50 && isExpanded) {
      return (
        <div>
          <pre className="whitespace-pre-wrap text-gray-700">{stringValue}</pre>
          <button
            onClick={() => toggleCellExpansion(cellKey)}
            className="mt-1 text-xs text-indigo-600 hover:text-indigo-700"
          >
            Свернуть
          </button>
        </div>
      );
    }

    return <span className="text-gray-700">{stringValue}</span>;
  };

  const totalPages = tableData?.total ? Math.ceil(tableData.total / pageSize) : 1;

  return (
    <div className="app-content py-8">
      <button
        onClick={() => navigate("/admin")}
        className="mb-4 text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
      >
        ← Назад в админку
      </button>

      <h1 className="text-2xl font-bold mb-6">База данных</h1>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {!selectedTable ? (
        // Tables list
        <div>
          {loading ? (
            <div className="text-center py-8">
              <p className="text-gray-500">Загрузка...</p>
            </div>
          ) : (
            <div className="space-y-2">
              {tables.map((table) => (
                <div
                  key={table.table_name}
                  onClick={() => handleTableClick(table.table_name)}
                  className="p-4 bg-white rounded-lg border border-gray-200 hover:border-indigo-300 cursor-pointer transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-medium text-gray-900">{table.table_name}</h3>
                      <p className="text-sm text-gray-500">
                        {table.columns_count} столбцов
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-semibold text-indigo-600">
                        ~{table.row_count_estimate.toLocaleString()}
                      </p>
                      <p className="text-xs text-gray-500">строк</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        // Table data view
        <div>
          <div className="mb-4 flex items-center justify-between">
            <button
              onClick={handleBack}
              className="text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
            >
              ← К списку таблиц
            </button>
            <h2 className="text-xl font-bold">{selectedTable}</h2>
          </div>

          {/* Search */}
          <form onSubmit={handleSearch} className="mb-4">
            <div className="flex gap-2">
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Поиск по текстовым столбцам..."
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <button
                type="submit"
                className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
              >
                Поиск
              </button>
              {search && (
                <button
                  type="button"
                  onClick={() => {
                    setSearch("");
                    setSearchInput("");
                    setPage(1);
                  }}
                  className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
                >
                  Сбросить
                </button>
              )}
            </div>
          </form>

          {loading ? (
            <div className="text-center py-8">
              <p className="text-gray-500">Загрузка...</p>
            </div>
          ) : tableData ? (
            <div>
              {/* Table */}
              <div className="overflow-x-auto bg-white rounded-lg border border-gray-200">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      {tableData.columns.map((column) => (
                        <th
                          key={column.name}
                          onClick={() => handleSort(column.name)}
                          className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                        >
                          <div className="flex items-center gap-1">
                            <span>{column.name}</span>
                            {column.is_primary_key && (
                              <span className="text-xs text-indigo-600">🔑</span>
                            )}
                            {column.masked && (
                              <span className="text-xs text-red-600">🔒</span>
                            )}
                            {orderBy === column.name && (
                              <span className="text-xs">
                                {orderDir === "asc" ? "↑" : "↓"}
                              </span>
                            )}
                          </div>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {tableData.rows.map((row, rowIndex) => (
                      <tr key={rowIndex} className="hover:bg-gray-50">
                        {tableData.columns.map((column) => (
                          <td
                            key={column.name}
                            className="px-4 py-3 text-sm max-w-xs"
                          >
                            {formatCellValue(row[column.name], column, rowIndex)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="mt-4 flex items-center justify-between">
                <div className="text-sm text-gray-600">
                  {tableData.total !== null ? (
                    <>
                      Страница {tableData.page} из {totalPages} • Всего: {tableData.total} записей
                    </>
                  ) : (
                    <>Страница {tableData.page}</>
                  )}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage(Math.max(1, page - 1))}
                    disabled={page === 1}
                    className="px-3 py-1 border border-gray-300 rounded disabled:opacity-50"
                  >
                    ←
                  </button>
                  <button
                    onClick={() => setPage(page + 1)}
                    disabled={tableData.rows.length < pageSize}
                    className="px-3 py-1 border border-gray-300 rounded disabled:opacity-50"
                  >
                    →
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-gray-500">Нет данных</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AdminDbPage;
