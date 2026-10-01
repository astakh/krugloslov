import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { EvaluateResponse, WordEvaluation, SuggestedWord } from '../types/lesson';

export default function ReviewPage() {
  const { lessonId, exerciseId } = useParams<{ lessonId: string; exerciseId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  
  const [showTranslation, setShowTranslation] = useState(false);
  
  // Load exercise result
  const { data: result, isLoading } = useQuery({
    queryKey: ['exercise-result', lessonId, exerciseId],
    queryFn: () => apiClient.get<EvaluateResponse>(`/lesson/${lessonId}/exercises/${exerciseId}/result`),
  });
  
  // Handle suggestion action
  const suggestionMutation = useMutation({
    mutationFn: ({ wordId, action }: { wordId: number; action: 'add' | 'ignore' }) =>
      apiClient.post(`/lesson/exercises/${exerciseId}/suggestions/${wordId}`, { action }),
    onSuccess: (_, variables) => {
      // Update local state
      queryClient.setQueryData(['exercise-result', lessonId, exerciseId], (old: any) => {
        if (!old) return old;
        return {
          ...old,
          suggestions: old.suggestions.map((s: SuggestedWord) =>
            s.word_id === variables.wordId
              ? { ...s, action: variables.action }
              : s
          ),
        };
      });
    },
  });
  
  // Handle report
  const reportMutation = useMutation({
    mutationFn: (data: { reason: string; comment: string }) =>
      apiClient.post(`/lesson/exercises/${exerciseId}/report`, data),
    onSuccess: () => {
      alert('Жалоба отправлена');
    },
    onError: (error: any) => {
      alert(error.response?.data?.error?.message || 'Ошибка отправки жалобы');
    },
  });
  
  const handleNext = async () => {
    if (result?.lesson_completed) {
      navigate(`/lesson/${lessonId}/complete`);
    } else {
      // Get next exercise and navigate directly to it
      try {
        const current = await apiClient.get<{
          exercise_id: number;
          sentence: string;
          order_index: number;
          exercises_done: number;
          exercises_total: number;
        }>(`/lesson/${lessonId}/current`);
        
        navigate(`/lesson/${lessonId}/exercise/${current.exercise_id}`);
      } catch (err) {
        const error = err as any;
        
        // If lesson is completed, redirect to summary
        if (error?.error?.code === "lesson_not_active") {
          navigate(`/lesson/${lessonId}/summary`);
          return;
        }
        
        // For other errors, redirect to home
        navigate('/');
      }
    }
  };
  
  const handleReport = () => {
    const reasons = [
      'bad_sentence - Проблема с предложением',
      'wrong_translation - Неправильный перевод',
      'grammar_error - Грамматическая ошибка',
      'other - Другое'
    ];
    
    const reasonInput = prompt(
      'Выберите причину жалобы:\n\n' + 
      reasons.join('\n') + 
      '\n\nВведите одно из: bad_sentence, wrong_translation, grammar_error, other'
    );
    
    if (!reasonInput) return;
    
    const reason = reasonInput.trim().toLowerCase();
    const validReasons = ['bad_sentence', 'wrong_translation', 'grammar_error', 'other'];
    
    if (!validReasons.includes(reason)) {
      alert('Недопустимая причина. Используйте одно из: bad_sentence, wrong_translation, grammar_error, other');
      return;
    }
    
    const comment = prompt('Комментарий (необязательно):') || '';
    
    reportMutation.mutate({ reason, comment });
  };
  
  if (isLoading) {
    return <div className="flex items-center justify-center min-h-screen">Загрузка...</div>;
  }
  
  if (!result) {
    return <div className="flex items-center justify-center min-h-screen">Результат не найден</div>;
  }
  
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-4 py-3">
        <div className="max-w-2xl mx-auto">
          <h1 className="text-lg font-medium text-gray-900">Разбор результата</h1>
        </div>
      </div>
      
      {/* Content */}
      <div className="flex-1 px-4 py-6">
        <div className="max-w-2xl mx-auto space-y-6">
          {/* Original sentence */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-sm font-medium text-gray-500 mb-2">Исходное предложение:</h2>
            <p className="text-lg text-gray-900">{result.target_sentence}</p>
          </div>
          
          {/* User translation */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-sm font-medium text-gray-500 mb-2">Ваш перевод:</h2>
            {result.user_translation ? (
              <p className="text-lg text-gray-900">{result.user_translation}</p>
            ) : (
              <p className="text-lg text-gray-400 italic">Не переведено</p>
            )}
          </div>
          
          {/* Word evaluations */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-sm font-medium text-gray-500 mb-4">Результаты по словам:</h2>
            <div className="space-y-4">
              {result.words.map((word: WordEvaluation) => (
                <div key={word.word_id} className="border-l-4 pl-4 py-2" style={{
                  borderColor: word.result === 'correct' ? '#10b981' :
                               word.result === 'typo' ? '#f59e0b' : '#ef4444'
                }}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-gray-900">
                      {word.lemma} <span className="text-gray-500 text-sm">({word.pos})</span>
                    </span>
                    <span className={`text-sm font-medium ${
                      word.result === 'correct' ? 'text-green-600' :
                      word.result === 'typo' ? 'text-yellow-600' : 'text-red-600'
                    }`}>
                      {word.result === 'correct' ? '✓ Верно' :
                       word.result === 'typo' ? '~ Опечатка' : '✗ Неверно'}
                    </span>
                  </div>
                  <div className="text-sm text-gray-600">
                    В предложении: <span className="font-medium">{word.surface_form}</span>
                  </div>
                  <div className="text-sm text-gray-600">
                    Ваш перевод: {word.user_fragment || <span className="italic text-gray-400">не переведено</span>}
                  </div>
                  <div className="text-sm text-gray-500 mt-1">
                    Переводы: {word.translations.join(', ')}
                  </div>
                </div>
              ))}
            </div>
          </div>
          
          {/* Reference translation */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <button
              onClick={() => setShowTranslation(!showTranslation)}
              className="w-full text-left"
            >
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-medium text-gray-500">Эталонный перевод:</h2>
                <span className="text-gray-400">{showTranslation ? '▲' : '▼'}</span>
              </div>
            </button>
            {showTranslation && (
              <p className="text-lg text-gray-900 mt-2">{result.reference_translation}</p>
            )}
          </div>
          
          {/* Suggestions */}
          {result.suggestions.length > 0 && (
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-sm font-medium text-gray-500 mb-4">Новые слова:</h2>
              <div className="space-y-3">
                {result.suggestions.map((suggestion: SuggestedWord) => (
                  <div key={suggestion.word_id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div>
                      <div className="font-medium text-gray-900">
                        {suggestion.lemma} <span className="text-gray-500 text-sm">({suggestion.pos})</span>
                      </div>
                      <div className="text-sm text-gray-600">
                        {suggestion.translations.join(', ')}
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => suggestionMutation.mutate({ wordId: suggestion.word_id, action: 'add' })}
                        disabled={suggestionMutation.isPending || (suggestion as any).action === 'add'}
                        className="px-3 py-1 bg-green-500 text-white text-sm rounded hover:bg-green-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
                      >
                        + Добавить
                      </button>
                      <button
                        onClick={() => suggestionMutation.mutate({ wordId: suggestion.word_id, action: 'ignore' })}
                        disabled={suggestionMutation.isPending || (suggestion as any).action === 'ignore'}
                        className="px-3 py-1 bg-red-500 text-white text-sm rounded hover:bg-red-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
                      >
                        × Не предлагать
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Report button */}
          <div className="text-center">
            <button
              onClick={handleReport}
              disabled={reportMutation.isPending}
              className="text-sm text-gray-500 hover:text-gray-700 underline disabled:opacity-50"
            >
              Пожаловаться на предложение
            </button>
          </div>
          
          {/* Next button */}
          <button
            onClick={handleNext}
            className="w-full bg-blue-500 text-white py-3 px-6 rounded-lg font-medium hover:bg-blue-600 transition-colors"
          >
            {result.lesson_completed ? 'Завершить урок' : 'Следующее упражнение'}
          </button>
        </div>
      </div>
    </div>
  );
}
