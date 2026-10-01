import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { Exercise, EvaluateResponse } from '../types/lesson';

export default function ExercisePage() {
  const { lessonId, exerciseId } = useParams<{ lessonId: string; exerciseId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  
  const [translation, setTranslation] = useState('');
  const [showExitModal, setShowExitModal] = useState(false);
  
  // Load exercise data
  const { data: exercise, isLoading } = useQuery({
    queryKey: ['exercise', lessonId, exerciseId],
    queryFn: () => apiClient.get<Exercise>(`/lesson/${lessonId}/exercises/${exerciseId}`),
  });
  
  // Evaluate translation mutation
  const evaluateMutation = useMutation({
    mutationFn: (data: { user_translation: string; dont_know: boolean }) =>
      apiClient.post<EvaluateResponse>('/lesson/evaluate', {
        exercise_id: Number(exerciseId),
        ...data,
      }),
    onSuccess: (response) => {
      // Clear draft
      localStorage.removeItem(`exercise_draft_${exerciseId}`);
      // Navigate to review
      navigate(`/lesson/${lessonId}/review/${exerciseId}`);
    },
    onError: (error: any) => {
      // Show error toast
      alert(error.response?.data?.error?.message || 'Ошибка проверки');
    },
  });
  
  // Load draft from localStorage
  useEffect(() => {
    const draft = localStorage.getItem(`exercise_draft_${exerciseId}`);
    if (draft) {
      setTranslation(draft);
    }
  }, [exerciseId]);
  
  // Save draft to localStorage
  useEffect(() => {
    if (translation) {
      localStorage.setItem(`exercise_draft_${exerciseId}`, translation);
    }
  }, [translation, exerciseId]);
  
  // Handle browser back button
  useEffect(() => {
    const handlePopState = () => {
      setShowExitModal(true);
      // Push state back to prevent navigation
      window.history.pushState(null, '', location.pathname);
    };
    
    window.addEventListener('popstate', handlePopState);
    window.history.pushState(null, '', location.pathname);
    
    return () => window.removeEventListener('popstate', handlePopState);
  }, [location]);
  
  // Handle beforeunload
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = '';
    };
    
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, []);
  
  const handleCheck = () => {
    if (!translation.trim()) return;
    evaluateMutation.mutate({
      user_translation: translation.trim(),
      dont_know: false,
    });
  };
  
  const handleDontKnow = () => {
    evaluateMutation.mutate({
      user_translation: '',
      dont_know: true,
    });
  };
  
  const handleReport = () => {
    // TODO: Open report modal
    alert('Функция жалобы будет реализована позже');
  };
  
  const handleExit = () => {
    setShowExitModal(false);
    navigate('/');
  };
  
  if (isLoading) {
    return <div className="flex items-center justify-center min-h-screen">Загрузка...</div>;
  }
  
  if (!exercise) {
    return <div className="flex items-center justify-center min-h-screen">Упражнение не найдено</div>;
  }
  
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-4 py-3">
        <div className="max-w-2xl mx-auto">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-600">
              Упражнение {exercise.order_index + 1} из {exercise.total_exercises}
            </div>
            <button
              onClick={() => setShowExitModal(true)}
              className="text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          </div>
          {/* Progress bar */}
          <div className="mt-2 h-1 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 transition-all"
              style={{ width: `${((exercise.order_index + 1) / exercise.total_exercises) * 100}%` }}
            />
          </div>
        </div>
      </div>
      
      {/* Content */}
      <div className="flex-1 px-4 py-6">
        <div className="max-w-2xl mx-auto">
          {/* Sentence */}
          <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
            <h2 className="text-xl font-medium text-gray-900 mb-2">
              Переведите предложение:
            </h2>
            <p className="text-lg text-gray-700">{exercise.target_sentence}</p>
          </div>
          
          {/* Target words */}
          {exercise.target_words && exercise.target_words.length > 0 && (
            <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
              <h3 className="text-sm font-medium text-gray-700 mb-3">
                Целевые слова для перевода:
              </h3>
              <div className="flex flex-wrap gap-2">
                {exercise.target_words.map((word) => (
                  <span
                    key={word.word_id}
                    className="inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium bg-blue-100 text-blue-800"
                  >
                    {word.lemma}
                    <span className="ml-1.5 text-xs text-blue-600">({word.pos})</span>
                  </span>
                ))}
              </div>
            </div>
          )}
          
          {/* Translation input */}
          <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Ваш перевод:
            </label>
            <textarea
              value={translation}
              onChange={(e) => setTranslation(e.target.value)}
              disabled={evaluateMutation.isPending}
              placeholder="Введите перевод на русский язык..."
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed resize-none"
              rows={4}
              maxLength={500}
            />
            <div className="mt-1 text-sm text-gray-500 text-right">
              {translation.length} / 500
            </div>
          </div>
          
          {/* Actions */}
          <div className="flex gap-3">
            <button
              onClick={handleCheck}
              disabled={!translation.trim() || evaluateMutation.isPending}
              className="flex-1 bg-blue-500 text-white py-3 px-6 rounded-lg font-medium hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              {evaluateMutation.isPending ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Проверка...
                </span>
              ) : (
                'Проверить'
              )}
            </button>
            <button
              onClick={handleDontKnow}
              disabled={evaluateMutation.isPending}
              className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50 disabled:bg-gray-100 disabled:cursor-not-allowed transition-colors"
            >
              Не знаю
            </button>
          </div>
          
          {/* Report button */}
          <div className="mt-4 text-center">
            <button
              onClick={handleReport}
              className="text-sm text-gray-500 hover:text-gray-700 underline"
            >
              Пожаловаться на предложение
            </button>
          </div>
        </div>
      </div>
      
      {/* Exit modal */}
      {showExitModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md mx-4">
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Выйти из урока?
            </h3>
            <p className="text-gray-600 mb-4">
              Прогресс сохранится. Вы сможете продолжить позже.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowExitModal(false)}
                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
              >
                Остаться
              </button>
              <button
                onClick={handleExit}
                className="flex-1 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
              >
                Выйти
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
