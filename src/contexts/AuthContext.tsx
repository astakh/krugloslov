/**
 * Authentication context and provider.
 * Manages access token in memory and handles 401 responses.
 */

import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import apiClient from "../api/client";

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  accessToken: string | null;
}

const AuthContext = createContext<AuthContextValue | null>(null);

interface TokenResponse {
  access_token: string;
  token_type: string;
}

/**
 * AuthProvider manages authentication state and provides auth methods.
 */
export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  
  // Ref for managing concurrent refresh requests
  const refreshPromiseRef = useRef<Promise<string> | null>(null);

  const isAuthenticated = accessToken !== null;

  /**
   * Refresh the access token using the refresh token cookie.
   * Deduplicates concurrent refresh requests.
   */
  const refreshAccessToken = useCallback(async (): Promise<string> => {
    // If a refresh is already in progress, wait for it
    if (refreshPromiseRef.current) {
      return refreshPromiseRef.current;
    }

    const promise = (async () => {
      try {
        const response = await apiClient.post<TokenResponse>("/auth/refresh");
        const newToken = response.access_token;
        setAccessToken(newToken);
        return newToken;
      } catch (error) {
        // Refresh failed — clear token and redirect to auth
        setAccessToken(null);
        navigate("/auth");
        throw error;
      } finally {
        refreshPromiseRef.current = null;
      }
    })();

    refreshPromiseRef.current = promise;
    return promise;
  }, [navigate]);

  /**
   * Login with email and password.
   */
  const login = useCallback(async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const response = await apiClient.post<TokenResponse>("/auth/login", { email, password });
      setAccessToken(response.access_token);
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Register with email and password.
   */
  const register = useCallback(async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const response = await apiClient.post<TokenResponse>("/auth/register", { email, password });
      setAccessToken(response.access_token);
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Logout and clear tokens.
   */
  const logout = useCallback(async () => {
    try {
      await apiClient.post("/auth/logout");
    } catch (error) {
      // Ignore errors during logout
      console.warn("Logout error:", error);
    } finally {
      setAccessToken(null);
      navigate("/auth");
    }
  }, [navigate]);

  // Register token provider with API client
  useEffect(() => {
    apiClient.setTokenProvider(() => accessToken);
  }, [accessToken]);

  // Listen for 401 events from API client
  useEffect(() => {
    const handleUnauthorized = async () => {
      try {
        await refreshAccessToken();
      } catch {
        // Refresh failed, already redirected in refreshAccessToken
      }
    };

    window.addEventListener("api:unauthorized", handleUnauthorized);
    return () => {
      window.removeEventListener("api:unauthorized", handleUnauthorized);
    };
  }, [refreshAccessToken]);

  const value: AuthContextValue = {
    isAuthenticated,
    isLoading,
    login,
    register,
    logout,
    accessToken,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

/**
 * Hook to access auth context.
 */
export const useAuth = (): AuthContextValue => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

export default AuthContext;
