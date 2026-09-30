/**
 * Hook to handle 401 Unauthorized responses.
 * Future: implement token refresh logic here.
 */
import { useEffect } from "react";

export function useAuthErrorHandler() {
  useEffect(() => {
    const handler = () => {
      // Future: redirect to /auth or refresh token
      console.warn("[Auth] Received 401 — authorization required");
    };

    window.addEventListener("api:unauthorized", handler);
    return () => {
      window.removeEventListener("api:unauthorized", handler);
    };
  }, []);
}
