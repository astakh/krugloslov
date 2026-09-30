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
            'You are an English language teacher. Generate {count} English sentences for a student at {level} level.

Requirements:
- Each sentence must contain the target word: {word}
- Sentences should be natural and contextually appropriate
- Use vocabulary appropriate for {level} level
- Each sentence should be 5-15 words long
- Provide a Russian translation for each sentence

Return JSON format:
{{
  "sentences": [
    {{
      "english": "English sentence with target word",
      "russian": "Russian translation"
    }}
  ]
}}',
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
