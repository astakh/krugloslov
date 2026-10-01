"""Add default prompts

Revision ID: 002_add_default_prompts
Revises: 001_initial_schema
Create Date: 2024-01-XX XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_default_prompts'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Insert default prompts
    op.execute("""
        INSERT INTO prompts (key, system_template, updated_at)
        VALUES 
        (
            'generate_sentences',
            'You are an English language teacher. Generate English sentences for a student at {level} level.

For each word group provided, create ONE natural English sentence that:
- Contains all the target words from that group
- Uses vocabulary appropriate for {level} level
- Is 5-15 words long
- Is contextually appropriate and natural

For each sentence, also provide:
- The exact surface form of each target word as used in the sentence
- A Russian translation of the complete sentence

Return JSON format EXACTLY as shown:
{{
  "groups": [
    {{
      "group_index": 0,
      "sentence": "English sentence with target words",
      "reference_translation": "Russian translation of the sentence",
      "words": [
        {{
          "lemma": "target_word_lemma",
          "pos": "noun|verb|adj|adv",
          "surface_form": "exact form used in sentence"
        }}
      ]
    }}
  ]
}}

IMPORTANT: 
- Use "groups" as the root key, NOT "sentences"
- Each group must have: group_index, sentence, reference_translation, words
- words array must contain all target words for that group with their surface forms
- Return ONLY valid JSON, no markdown, no explanations',
            NOW()
        ),
        (
            'evaluate_translation',
            'You are an English language teacher evaluating a student''s translation.

Compare the user''s translation with the reference translation and determine if the target words were translated correctly.

Rules:
- Focus on the target words, not the entire sentence
- Accept synonyms and grammatically correct variations
- Mark as "correct" if meaning is preserved
- Mark as "incorrect" if meaning is lost or wrong
- Mark as "partial" if some target words are correct

Return JSON format:
{{
  "results": [
    {{
      "word": "target word",
      "status": "correct|incorrect|partial",
      "feedback": "brief explanation"
    }}
  ],
  "overall": "correct|incorrect|partial"
}}',
            NOW()
        )
    """)


def downgrade() -> None:
    # Remove default prompts
    op.execute("""
        DELETE FROM prompts 
        WHERE key IN ('generate_sentences', 'evaluate_translation')
    """)
