import React, { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import apiClient from "../api/client";

const LessonPage: React.FC = () => {
  const navigate = useNavigate();
  const { lessonId } = useParams<{ lessonId: string }>();

  useEffect(() => {
    // If we have a lessonId, try to get current exercise and redirect
    if (lessonId) {
      const fetchCurrentExercise = async () => {
        try {
          const data = await apiClient.get<{
            exercise_id: number;
            sentence: string;
            order_index: number;
            exercises_done: number;
            exercises_total: number;
          }>(`/lesson/${lessonId}/current`);
          
          // Redirect to the current exercise
          navigate(`/lesson/${lessonId}/exercise/${data.exercise_id}`, { replace: true });
        } catch (err) {
          const error = err as any;
          
          // If lesson is completed, redirect to summary
          if (error?.error?.code === "lesson_not_active") {
            navigate(`/lesson/${lessonId}/summary`, { replace: true });
            return;
          }
          
          // If lesson not found, redirect to preview
          if (error?.error?.code === "lesson_not_found") {
            navigate("/lesson/preview", { replace: true });
            return;
          }
          
          // For other errors, redirect to preview
          navigate("/lesson/preview", { replace: true });
        }
      };
      
      fetchCurrentExercise();
    } else {
      // No lessonId, redirect to preview
      navigate("/lesson/preview", { replace: true });
    }
  }, [lessonId, navigate]);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <div className="text-5xl mb-4 animate-pulse">⏳</div>
        <p className="text-gray-600">Загрузка урока...</p>
      </div>
    </div>
  );
};

export default LessonPage;
