"""Add words_per_lesson to learning_profiles

Revision ID: 003_add_words_per_lesson
Revises: 002_add_default_prompts
Create Date: 2024-01-XX XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_add_words_per_lesson'
down_revision: Union[str, None] = '002_add_default_prompts'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add words_per_lesson column to learning_profiles
    op.add_column(
        'learning_profiles',
        sa.Column('words_per_lesson', sa.Integer(), nullable=False, server_default='10')
    )
    
    # Add check constraint
    op.create_check_constraint(
        'ck_learning_profiles_words_per_lesson',
        'learning_profiles',
        'words_per_lesson >= 1'
    )


def downgrade() -> None:
    # Drop check constraint
    op.drop_constraint('ck_learning_profiles_words_per_lesson', 'learning_profiles', type_='check')
    
    # Drop column
    op.drop_column('learning_profiles', 'words_per_lesson')
