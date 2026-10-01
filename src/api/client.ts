/**
 * Unified error response shape from the backend.
 */
export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}

/**
 * Token provider function type.
 */
export type TokenProvider = () => string | null;

/**
 * Base API client for communicating with the backend.
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

class ApiClient {
  private baseUrl: string;
  private tokenProvider: TokenProvider | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  /**
   * Set a function that returns the current access token.
   * This allows the client to get the token from React context.
   */
  setTokenProvider(provider: TokenProvider): void {
    this.tokenProvider = provider;
  }

  private async request<T>(
    method: string,
    path: string,
    options?: RequestInit
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;

    // Get access token if provider is set
    const token = this.tokenProvider ? this.tokenProvider() : null;

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options?.headers as Record<string, string>),
    };

    // Add Authorization header if token is available
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(url, {
      method,
      headers,
      credentials: "include", // Include cookies for refresh token
      ...options,
    });

    // Don't dispatch unauthorized event for refresh requests to avoid infinite loop
    const isRefreshRequest = path.includes("/auth/refresh");
    
    // Only dispatch unauthorized event for 401 status, not for 409 or other errors
    if (response.status === 401 && !isRefreshRequest) {
      // Dispatch event for auth context to handle
      window.dispatchEvent(new CustomEvent("api:unauthorized"));
    }

    if (!response.ok) {
      const errorData: ApiError = await response.json().catch(() => ({
        error: {
          code: "unknown_error",
          message: "Неизвестная ошибка",
          details: {},
        },
      }));
      throw errorData;
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return response.json();
  }

  async get<T>(path: string): Promise<T> {
    return this.request<T>("GET", path);
  }

  async post<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>("POST", path, {
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  async put<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>("PUT", path, {
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  async patch<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>("PATCH", path, {
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  async delete<T>(path: string): Promise<T> {
    return this.request<T>("DELETE", path);
  }
}

export const apiClient = new ApiClient(API_BASE_URL);
export default apiClient;
