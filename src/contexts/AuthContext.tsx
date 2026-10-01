/**
 * Authentication context and provider.
 * Manages access token in memory and handles 401 responses.
 */

import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import apiClient from "../api/client";

interface UserInfo {
  id: number;
  email: string;
  is_onboarded: boolean;
  is_admin: boolean;
}

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: UserInfo | null;
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  accessToken: string | null;
  completeOnboarding: () => Promise<void>;
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
  const [user, setUser] = useState<UserInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true); // Start with loading true
  const navigate = useNavigate();
  
  // Ref for managing concurrent refresh requests
  const refreshPromiseRef = useRef<Promise<string> | null>(null);
  
  // Ref to track if session restoration has been attempted
  const sessionRestoredRef = useRef(false);

  const isAuthenticated = accessToken !== null;

  /**
   * Fetch current user info from /auth/me
   */
  const fetchUserInfo = useCallback(async (token: string): Promise<UserInfo> => {
    const response = await fetch("/api/auth/me", {
      headers: {
        Authorization: `Bearer ${token}`,
      },
      credentials: "include",
    });
    
    if (!response.ok) {
      throw new Error("Failed to fetch user info");
    }
    
    return response.json();
  }, []);

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
        
        // Fetch user info with new token
        try {
          const userInfo = await fetchUserInfo(newToken);
          setUser(userInfo);
        } catch {
          // Ignore user info fetch errors during refresh
        }
        
        return newToken;
      } catch (error) {
        // Refresh failed — clear token and redirect to auth
        setAccessToken(null);
        setUser(null);
        navigate("/auth");
        throw error;
      } finally {
        refreshPromiseRef.current = null;
      }
    })();

    refreshPromiseRef.current = promise;
    return promise;
  }, [navigate, fetchUserInfo]);

  /**
   * Login with email and password.
   */
  const login = useCallback(async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const response = await apiClient.post<TokenResponse>("/auth/login", { email, password });
      const token = response.access_token;
      setAccessToken(token);
      
      // Fetch user info
      const userInfo = await fetchUserInfo(token);
      setUser(userInfo);
      
      // Redirect based on onboarding status
      if (!userInfo.is_onboarded) {
        navigate("/onboarding");
      } else {
        navigate("/");
      }
    } finally {
      setIsLoading(false);
    }
  }, [navigate, fetchUserInfo]);

  /**
   * Register with email and password.
   */
  const register = useCallback(async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const response = await apiClient.post<TokenResponse>("/auth/register", { email, password });
      const token = response.access_token;
      setAccessToken(token);
      
      // Fetch user info
      const userInfo = await fetchUserInfo(token);
      setUser(userInfo);
      
      // After registration, always go to onboarding
      navigate("/onboarding");
    } finally {
      setIsLoading(false);
    }
  }, [navigate, fetchUserInfo]);

  /**
   * Complete onboarding and update user state.
   */
  const completeOnboarding = useCallback(async () => {
    // Call the onboarding complete endpoint
    // This is handled by the OnboardingPage component
    // After completion, update user state
    if (accessToken) {
      try {
        const userInfo = await fetchUserInfo(accessToken);
        setUser(userInfo);
      } catch {
        // Ignore errors
      }
    }
  }, [accessToken, fetchUserInfo]);

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
      setUser(null);
      navigate("/auth");
    }
  }, [navigate]);

  // Register token provider with API client
  useEffect(() => {
    apiClient.setTokenProvider(() => accessToken);
  }, [accessToken]);

  // Redirect to onboarding if authenticated but not onboarded
  useEffect(() => {
    if (user && !user.is_onboarded) {
      const currentPath = window.location.pathname;
      // Only redirect if not already on onboarding or auth pages
      if (currentPath !== "/onboarding" && currentPath !== "/auth" && currentPath !== "/register") {
        navigate("/onboarding");
      }
    }
  }, [user, navigate]);

  // Listen for 401 events from API client
  useEffect(() => {
    let isRefreshing = false;
    
    const handleUnauthorized = async () => {
      // Only try to refresh if we have an access token
      // (otherwise we're not authenticated yet)
      if (!accessToken || isRefreshing) {
        return;
      }
      
      isRefreshing = true;
      
      try {
        await refreshAccessToken();
      } catch {
        // Refresh failed, already redirected in refreshAccessToken
      } finally {
        isRefreshing = false;
      }
    };

    window.addEventListener("api:unauthorized", handleUnauthorized);
    return () => {
      window.removeEventListener("api:unauthorized", handleUnauthorized);
    };
  }, [refreshAccessToken, accessToken]);

  // Restore session on app load using refresh token
  useEffect(() => {
    // Only attempt session restoration once
    if (sessionRestoredRef.current) {
      setIsLoading(false);
      return;
    }
    
    sessionRestoredRef.current = true;

    const restoreSession = async () => {
      try {
        // Try to refresh token on app load
        const response = await apiClient.post<TokenResponse>("/auth/refresh");
        const newToken = response.access_token;
        setAccessToken(newToken);
        
        // Fetch user info with new token
        const userInfo = await fetchUserInfo(newToken);
        setUser(userInfo);
      } catch {
        // No valid session, user needs to login
        setAccessToken(null);
        setUser(null);
        // Don't redirect here - let the app handle routing based on auth state
      } finally {
        setIsLoading(false);
      }
    };

    restoreSession();
  }, [fetchUserInfo]);

  const value: AuthContextValue = {
    isAuthenticated,
    isLoading,
    user,
    login,
    register,
    logout,
    accessToken,
    completeOnboarding,
  };

  // Show loading screen while restoring session
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="text-2xl mb-4">⏳</div>
          <p className="text-gray-600">Загрузка...</p>
        </div>
      </div>
    );
  }

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
