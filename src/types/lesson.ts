export interface TargetWord {
  word_id: number;
  lemma: string;
  pos: string;
}

export interface Exercise {
  id: number;
  order_index: number;
  total_exercises: number;
  target_sentence: string;
  status: 'pending' | 'evaluated';
  target_words: TargetWord[];
}

export interface WordEvaluation {
  word_id: number;
  lemma: string;
  pos: string;
  surface_form: string;
  result: 'correct' | 'typo' | 'incorrect';
  user_fragment: string | null;
  translations: string[];
}

export interface SuggestedWord {
  word_id: number;
  lemma: string;
  pos: string;
  translations: string[];
  action?: 'add' | 'ignore';
}

export interface EvaluateResponse {
  exercise_id: number;
  target_sentence: string;
  reference_translation: string;
  user_translation: string | null;
  words: WordEvaluation[];
  suggestions: SuggestedWord[];
  lesson_completed: boolean;
}
