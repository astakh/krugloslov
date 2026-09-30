import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import apiClient, { ApiError } from "../api/client";

// Common timezones for the select
const COMMON_TIMEZONES = [
  "Europe/London",
  "Europe/Paris",
  "Europe/Berlin",
  "Europe/Moscow",
  "Europe/Kiev",
  "Europe/Warsaw",
  "Europe/Prague",
  "Europe/Vienna",
  "Europe/Rome",
  "Europe/Madrid",
  "Europe/Amsterdam",
  "Europe/Brussels",
  "Europe/Stockholm",
  "Europe/Helsinki",
  "Europe/Athens",
  "Europe/Istanbul",
  "Asia/Dubai",
  "Asia/Tehran",
  "Asia/Karachi",
  "Asia/Kolkata",
  "Asia/Bangkok",
  "Asia/Singapore",
  "Asia/Hong_Kong",
  "Asia/Shanghai",
  "Asia/Tokyo",
  "Asia/Seoul",
  "Australia/Sydney",
  "Pacific/Auckland",
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "America/Toronto",
  "America/Vancouver",
  "America/Mexico_City",
  "America/Sao_Paulo",
  "America/Buenos_Aires",
  "Africa/Cairo",
  "Africa/Johannesburg",
  "Africa/Lagos",
];

// Level descriptions
const LEVELS = [
  {
    value: "A1",
    title: "A1 — Начальный",
    description: "Понимаю и могу использовать простые повседневные фразы",
  },
  {
    value: "A2",
    title: "A2 — Элементарный",
    description: "Понимаю предложения и часто используемые выражения",
  },
  {
    value: "B1",
    title: "B1 — Средний",
    description: "Понимаю основные идеи понятных текстов, могу общаться на большинство тем",
  },
  {
    value: "B2",
    title: "B2 — Выше среднего",
    description: "Понимаю сложные тексты, могу свободно общаться с носителями языка",
  },
];

const OnboardingPage: React.FC = () => {
  const [step, setStep] = useState(1);
  const [timezone, setTimezone] = useState("");
  const [level, setLevel] = useState("A1");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const { completeOnboarding, user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    // Set default timezone from browser
    try {
      const browserTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
      if (browserTimezone) {
        setTimezone(browserTimezone);
      }
    } catch {
      // Fallback to UTC
      setTimezone("UTC");
    }
  }, []);

  const handleNext = () => {
    if (step === 1) {
      if (!timezone) {
        setError("Выберите часовой пояс");
        return;
      }
      setError(null);
      setStep(2);
    }
  };

  const handleBack = () => {
    if (step === 2) {
      setError(null);
      setStep(1);
    }
  };

  const handleSubmit = async () => {
    if (!timezone || !level) {
      setError("Заполните все поля");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      await apiClient.post("/onboarding/complete", {
        timezone,
        level,
      });
      
      // Update user state in context
      await completeOnboarding();
      
      // Navigate to home
      navigate("/");
    } catch (err) {
      const apiError = err as ApiError;
      if (apiError.error) {
        if (apiError.error.code === "already_onboarded") {
          navigate("/");
        } else if (apiError.error.code === "general_dictionary_missing") {
          setError("Общий словарь не найден. Обратитесь к администратору.");
        } else {
          setError(apiError.error.message || "Произошла ошибка");
        }
      } else {
        setError("Произошла ошибка. Попробуйте позже.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl shadow-lg p-8">
          <h1 className="text-2xl font-bold text-center mb-2">Добро пожаловать!</h1>
          <p className="text-center text-gray-600 mb-6">
            Настройте параметры для начала обучения
          </p>

          {/* Language info */}
          <div className="mb-6 p-4 bg-indigo-50 rounded-lg border border-indigo-100">
            <p className="text-sm text-indigo-900">
              <strong>Изучаемый язык:</strong> Английский 🇬🇧
            </p>
            <p className="text-sm text-indigo-900 mt-1">
              <strong>Перевод на:</strong> Русский 🇷🇺
            </p>
          </div>

          {/* Progress indicator */}
          <div className="flex items-center justify-center mb-6">
            <div className={`w-3 h-3 rounded-full ${step >= 1 ? "bg-indigo-600" : "bg-gray-300"}`} />
            <div className="w-12 h-0.5 bg-gray-300 mx-2" />
            <div className={`w-3 h-3 rounded-full ${step >= 2 ? "bg-indigo-600" : "bg-gray-300"}`} />
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          {/* Step 1: Timezone */}
          {step === 1 && (
            <div>
              <h2 className="text-lg font-semibold mb-4">Шаг 1: Часовой пояс</h2>
              
              <div className="mb-6">
                <label htmlFor="timezone" className="block text-sm font-medium text-gray-700 mb-2">
                  Выберите ваш часовой пояс
                </label>
                <select
                  id="timezone"
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  {COMMON_TIMEZONES.map((tz) => (
                    <option key={tz} value={tz}>
                      {tz.replace(/_/g, " ")}
                    </option>
                  ))}
                </select>
              </div>

              <button
                onClick={handleNext}
                className="w-full py-2 px-4 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg transition-colors"
              >
                Далее
              </button>
            </div>
          )}

          {/* Step 2: Level */}
          {step === 2 && (
            <div>
              <h2 className="text-lg font-semibold mb-4">Шаг 2: Ваш уровень</h2>
              
              <div className="mb-6 space-y-3">
                {LEVELS.map((lvl) => (
                  <label
                    key={lvl.value}
                    className={`block p-4 border-2 rounded-lg cursor-pointer transition-colors ${
                      level === lvl.value
                        ? "border-indigo-600 bg-indigo-50"
                        : "border-gray-200 hover:border-gray-300"
                    }`}
                  >
                    <input
                      type="radio"
                      name="level"
                      value={lvl.value}
                      checked={level === lvl.value}
                      onChange={(e) => setLevel(e.target.value)}
                      className="sr-only"
                    />
                    <div className="font-medium text-gray-900">{lvl.title}</div>
                    <div className="text-sm text-gray-600 mt-1">{lvl.description}</div>
                  </label>
                ))}
              </div>

              <div className="flex gap-3">
                <button
                  onClick={handleBack}
                  className="flex-1 py-2 px-4 bg-gray-200 hover:bg-gray-300 text-gray-700 font-medium rounded-lg transition-colors"
                >
                  Назад
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={isSubmitting}
                  className="flex-1 py-2 px-4 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white font-medium rounded-lg transition-colors"
                >
                  {isSubmitting ? "Завершение..." : "Завершить"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default OnboardingPage;
