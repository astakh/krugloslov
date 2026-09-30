import React, { useEffect, useState } from "react";
import apiClient from "../api/client";

interface User {
  id: number;
  email: string;
  is_onboarded: boolean;
  is_admin: boolean;
  created_at: string;
}

interface UsersListResponse {
  users: User[];
  total: number;
  page: number;
  page_size: number;
}

interface ResetPasswordResponse {
  message: string;
  user_id: number;
  temporary_password: string;
}

const AdminUsersPage: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [searchTimeout, setSearchTimeout] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [resettingUserId, setResettingUserId] = useState<number | null>(null);
  const [tempPassword, setTempPassword] = useState<string | null>(null);
  const [resetError, setResetError] = useState<string | null>(null);
  
  const pageSize = 20;

  useEffect(() => {
    loadUsers();
  }, [page, search]);

  const loadUsers = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params = new URLSearchParams();
      params.append("page", page.toString());
      params.append("page_size", pageSize.toString());
      
      if (search.trim()) {
        params.append("search", search.trim());
      }
      
      const data = await apiClient.get<UsersListResponse>(
        `/admin/users?${params.toString()}`
      );
      
      setUsers(data.users);
      setTotal(data.total);
    } catch (err) {
      setError("Не удалось загрузить пользователей");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearch(value);
    
    if (searchTimeout) {
      clearTimeout(searchTimeout);
    }
    
    const timeout = setTimeout(() => {
      setPage(1);
    }, 300);
    
    setSearchTimeout(timeout);
  };

  const handleResetPassword = async (userId: number) => {
    if (!confirm("Вы уверены, что хотите сбросить пароль этому пользователю? Все его сессии будут отозваны.")) {
      return;
    }

    setResettingUserId(userId);
    setResetError(null);
    setTempPassword(null);

    try {
      const response = await apiClient.post<ResetPasswordResponse>(
        `/admin/users/${userId}/reset-password`
      );
      
      setTempPassword(response.temporary_password);
    } catch (err: any) {
      setResetError(err.error?.message || "Не удалось сбросить пароль");
    } finally {
      setResettingUserId(null);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString("ru-RU");
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="app-content py-8">
      <h1 className="text-2xl font-bold mb-6">Пользователи</h1>

      {/* Search */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-6">
        <input
          type="text"
          placeholder="Поиск по email..."
          value={search}
          onChange={handleSearchChange}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      {/* Temporary password modal */}
      {tempPassword && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-md w-full p-6">
            <h2 className="text-xl font-bold mb-4">Пароль сброшен</h2>
            <p className="text-sm text-gray-600 mb-4">
              Временный пароль для пользователя. Сообщите его пользователю и попросите сменить при следующем входе.
            </p>
            <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg mb-4">
              <p className="text-sm font-mono text-gray-900 break-all">
                {tempPassword}
              </p>
            </div>
            <p className="text-xs text-red-600 mb-4">
              ⚠️ Этот пароль показывается только один раз. Скопируйте его сейчас.
            </p>
            <button
              onClick={() => {
                navigator.clipboard.writeText(tempPassword);
                setTempPassword(null);
              }}
              className="w-full px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg"
            >
              Скопировать и закрыть
            </button>
          </div>
        </div>
      )}

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

      {/* Users list */}
      {!loading && users.length === 0 && (
        <div className="text-center py-8">
          <p className="text-gray-500">Пользователей не найдено</p>
        </div>
      )}

      {!loading && users.length > 0 && (
        <>
          <div className="space-y-3">
            {users.map((user) => (
              <div
                key={user.id}
                className="bg-white rounded-lg border border-gray-200 p-4"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-gray-900">
                        {user.email}
                      </span>
                      {user.is_admin && (
                        <span className="px-2 py-1 text-xs font-medium bg-purple-100 text-purple-800 rounded">
                          Админ
                        </span>
                      )}
                      {user.is_onboarded ? (
                        <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded">
                          Онбординг пройден
                        </span>
                      ) : (
                        <span className="px-2 py-1 text-xs font-medium bg-yellow-100 text-yellow-800 rounded">
                          Онбординг не пройден
                        </span>
                      )}
                    </div>
                    <div className="text-sm text-gray-500">
                      ID: {user.id} • Регистрация: {formatDate(user.created_at)}
                    </div>
                  </div>
                  <button
                    onClick={() => handleResetPassword(user.id)}
                    disabled={resettingUserId === user.id}
                    className="px-3 py-1 bg-red-100 hover:bg-red-200 text-red-700 text-sm rounded disabled:opacity-50"
                  >
                    {resettingUserId === user.id ? "Сброс..." : "Сбросить пароль"}
                  </button>
                </div>

                {resetError && resettingUserId === user.id && (
                  <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded">
                    <p className="text-xs text-red-600">{resetError}</p>
                  </div>
                )}
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
    </div>
  );
};

export default AdminUsersPage;
