"""initial schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"),
        sa.Column("timezone_changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("is_onboarded", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email_lower", "users", [sa.text("lower(email)")], unique=True)

    # --- refresh_tokens ---
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("family_id", sa.String(64), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["replaced_by"], ["refresh_tokens.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"])
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"])
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])

    # --- dictionaries ---
    op.create_table(
        "dictionaries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_general", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(
        "ix_dictionaries_is_general_unique",
        "dictionaries",
        ["is_general"],
        unique=True,
        postgresql_where=sa.text("is_general = true"),
    )

    # --- words ---
    op.create_table(
        "words",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("lemma", sa.String(255), nullable=False),
        sa.Column("lemma_key", sa.String(255), nullable=False),
        sa.Column("pos", sa.String(10), nullable=False),
        sa.Column("level", sa.String(2), nullable=True),
        sa.Column("translations", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lemma_key", "pos", name="uq_words_lemma_key_pos"),
        sa.CheckConstraint(
            "pos IN ('noun', 'verb', 'adj', 'adv', 'pron', 'prep', 'conj', 'num', 'det', 'intj')",
            name="ck_words_pos",
        ),
        sa.CheckConstraint(
            "level IS NULL OR level IN ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')",
            name="ck_words_level",
        ),
    )

    # --- dictionary_words ---
    op.create_table(
        "dictionary_words",
        sa.Column("dictionary_id", sa.Integer(), nullable=False),
        sa.Column("word_id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("dictionary_id", "word_id"),
        sa.ForeignKeyConstraint(["dictionary_id"], ["dictionaries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["word_id"], ["words.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("dictionary_id", "word_id", name="uq_dictionary_words_dict_word"),
    )

    # --- learning_profiles ---
    op.create_table(
        "learning_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(2), nullable=False, server_default="A1"),
        sa.Column("dictionary_id", sa.Integer(), nullable=False),
        sa.Column("daily_lesson_limit", sa.Integer(), nullable=False, server_default=sa.text("5")),
        sa.Column("last_lesson_number", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["dictionary_id"], ["dictionaries.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("user_id"),
        sa.CheckConstraint(
            "level IN ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')",
            name="ck_learning_profiles_level",
        ),
        sa.CheckConstraint("daily_lesson_limit >= 1", name="ck_learning_profiles_daily_limit"),
    )

    # --- user_words ---
    op.create_table(
        "user_words",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("learning_profile_id", sa.Integer(), nullable=False),
        sa.Column("word_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("stage", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("due_lesson_number", sa.Integer(), nullable=True),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(16), nullable=False, server_default="dictionary"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["learning_profile_id"], ["learning_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["word_id"], ["words.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("learning_profile_id", "word_id", name="uq_user_words_profile_word"),
        sa.CheckConstraint(
            "status IN ('active', 'mastered', 'ignored')",
            name="ck_user_words_status",
        ),
        sa.CheckConstraint(
            "source IN ('dictionary', 'suggestion', 'decline')",
            name="ck_user_words_source",
        ),
        sa.CheckConstraint("stage >= 0 AND stage <= 6", name="ck_user_words_stage"),
        sa.CheckConstraint(
            "status = 'active' OR due_lesson_number IS NULL",
            name="ck_user_words_due_only_active",
        ),
    )
    op.create_index(
        "ix_user_words_profile_status_due",
        "user_words",
        ["learning_profile_id", "status", "due_lesson_number"],
    )

    # --- lessons ---
    op.create_table(
        "lessons",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("learning_profile_id", sa.Integer(), nullable=False),
        sa.Column("lesson_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="in_progress"),
        sa.Column("words_per_lesson", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_local_date", sa.Date(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_local_date", sa.Date(), nullable=True),
        sa.Column("abandoned_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["learning_profile_id"], ["learning_profiles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("learning_profile_id", "lesson_number", name="uq_lessons_profile_number"),
        sa.CheckConstraint(
            "status IN ('in_progress', 'completed', 'abandoned')",
            name="ck_lessons_status",
        ),
    )
    op.create_index(
        "ix_lessons_profile_in_progress_unique",
        "lessons",
        ["learning_profile_id"],
        unique=True,
        postgresql_where=sa.text("status = 'in_progress'"),
    )
    op.create_index(
        "ix_lessons_profile_started_local_date",
        "lessons",
        ["learning_profile_id", "started_local_date"],
    )
    op.create_index("ix_lessons_completed_local_date", "lessons", ["completed_local_date"])

    # --- lesson_exercises ---
    op.create_table(
        "lesson_exercises",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("target_sentence", sa.Text(), nullable=False),
        sa.Column("reference_translation", sa.Text(), nullable=False),
        sa.Column("user_translation", sa.Text(), nullable=True),
        sa.Column("dont_know", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "status IN ('pending', 'evaluated')",
            name="ck_exercises_status",
        ),
    )
    op.create_index("ix_exercises_lesson_id", "lesson_exercises", ["lesson_id"])

    # --- lesson_exercise_words ---
    op.create_table(
        "lesson_exercise_words",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("exercise_id", sa.Integer(), nullable=False),
        sa.Column("word_id", sa.Integer(), nullable=False),
        sa.Column("is_target", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_new", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("surface_form", sa.String(255), nullable=True),
        sa.Column("result", sa.String(16), nullable=True),
        sa.Column("user_fragment", sa.String(255), nullable=True),
        sa.Column("stage_before", sa.Integer(), nullable=True),
        sa.Column("stage_after", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["exercise_id"], ["lesson_exercises.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["word_id"], ["words.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "result IS NULL OR result IN ('correct', 'typo', 'incorrect')",
            name="ck_exercise_words_result",
        ),
        sa.CheckConstraint(
            "stage_before IS NULL OR (stage_before >= 0 AND stage_before <= 6)",
            name="ck_exercise_words_stage_before",
        ),
        sa.CheckConstraint(
            "stage_after IS NULL OR (stage_after >= 0 AND stage_after <= 6)",
            name="ck_exercise_words_stage_after",
        ),
    )
    op.create_index("ix_exercise_words_exercise_id", "lesson_exercise_words", ["exercise_id"])
    op.create_index("ix_exercise_words_word_id", "lesson_exercise_words", ["word_id"])

    # --- lesson_exercise_suggestions ---
    op.create_table(
        "lesson_exercise_suggestions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("exercise_id", sa.Integer(), nullable=False),
        sa.Column("word_id", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(16), nullable=False, server_default="suggested"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["exercise_id"], ["lesson_exercises.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["word_id"], ["words.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("exercise_id", "word_id", name="uq_suggestions_exercise_word"),
        sa.CheckConstraint(
            "state IN ('suggested', 'added', 'ignored')",
            name="ck_suggestions_state",
        ),
    )

    # --- sentence_reports ---
    op.create_table(
        "sentence_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("exercise_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(16), nullable=False, server_default="new"),
        sa.Column("admin_note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["exercise_id"], ["lesson_exercises.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "exercise_id", name="uq_reports_user_exercise"),
        sa.CheckConstraint(
            "status IN ('new', 'processed')",
            name="ck_reports_status",
        ),
    )

    # --- llm_calls ---
    op.create_table(
        "llm_calls",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("purpose", sa.String(16), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=True),
        sa.Column("exercise_id", sa.Integer(), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("request", postgresql.JSONB(), nullable=True),
        sa.Column("response", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["exercise_id"], ["lesson_exercises.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "purpose IN ('generate', 'evaluate')",
            name="ck_llm_calls_purpose",
        ),
        sa.CheckConstraint(
            "status IN ('ok', 'http_error', 'timeout', 'invalid_json', 'invalid_schema', 'validation_failed')",
            name="ck_llm_calls_status",
        ),
    )
    op.create_index("ix_llm_calls_user_id", "llm_calls", ["user_id"])
    op.create_index("ix_llm_calls_created_at", "llm_calls", ["created_at"])

    # --- events ---
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_events_user_id_type", "events", ["user_id", "type"])
    op.create_index("ix_events_created_at", "events", ["created_at"])

    # --- dictionary_imports ---
    op.create_table(
        "dictionary_imports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("admin_id", sa.Integer(), nullable=True),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("dictionary_id", sa.Integer(), nullable=False),
        sa.Column("added_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("linked_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("skipped_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("errors_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("report", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["admin_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["dictionary_id"], ["dictionaries.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_dictionary_imports_sha256", "dictionary_imports", ["sha256"])

    # --- prompts ---
    op.create_table(
        "prompts",
        sa.Column("key", sa.String(128), nullable=False),
        sa.Column("system_template", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("key"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
    )

    # --- prompt_history ---
    op.create_table(
        "prompt_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("key", sa.String(128), nullable=False),
        sa.Column("system_template", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["key"], ["prompts.key"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_prompt_history_key_created_at", "prompt_history", ["key", "created_at"])


def downgrade() -> None:
    op.drop_table("prompt_history")
    op.drop_table("prompts")
    op.drop_table("dictionary_imports")
    op.drop_table("events")
    op.drop_table("llm_calls")
    op.drop_table("sentence_reports")
    op.drop_table("lesson_exercise_suggestions")
    op.drop_table("lesson_exercise_words")
    op.drop_table("lesson_exercises")
    op.drop_table("lessons")
    op.drop_table("user_words")
    op.drop_table("learning_profiles")
    op.drop_table("dictionary_words")
    op.drop_table("words")
    op.drop_table("dictionaries")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
