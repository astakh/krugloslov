"""Dictionary import service."""

from __future__ import annotations

import hashlib
import unicodedata
from typing import List, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dictionary import Dictionary
from app.models.word import VALID_LEVELS, VALID_POS
from app.repositories.word_repo import normalize_lemma
from app.schemas.admin import (
    DictionaryImportInput,
    DictionaryReport,
    DryRunReport,
    ErrorDetail,
    ImportReport,
)


class DictionaryImportService:
    """Service for importing dictionaries from JSON files."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def import_dictionary(
        self,
        admin_id: int,
        file_name: str,
        file_content: bytes,
        dry_run: bool = False,
    ) -> Tuple[ImportReport, str]:
        """Import dictionary from JSON file.

        Args:
            admin_id: ID of the admin performing the import.
            file_name: Name of the uploaded file.
            file_content: Raw file content.
            dry_run: If True, only validate without writing.

        Returns:
            Tuple of (report, sha256_hash).
        """
        # Calculate SHA256
        sha256 = hashlib.sha256(file_content).hexdigest()

        # Parse JSON
        import json
        try:
            data = json.loads(file_content.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise ValueError(f"Invalid JSON: {e}")

        # Validate schema
        try:
            import_data = DictionaryImportInput(**data)
        except Exception as e:
            raise ValueError(f"Invalid schema: {e}")

        # Check file-level constraints
        if len(import_data.words) > 50000:
            raise ValueError("Too many words (max 50000)")

        # Get or create dictionary
        dict_report, dictionary = await self._get_or_create_dictionary(
            import_data.dictionary, dry_run
        )

        # Validate and process words
        valid_words, error_details = self._validate_words(
            import_data.words, dict_report.created and import_data.dictionary.is_general
        )

        if dry_run:
            return DryRunReport(
                dictionary=dict_report,
                total_words=len(import_data.words),
                valid_words=len(valid_words),
                skipped=len(import_data.words) - len(valid_words),
                errors=len(error_details),
                error_details=error_details[:200],
            ), sha256

        # Apply import with advisory lock
        report = await self._apply_import(
            admin_id, file_name, sha256, dictionary, valid_words, error_details
        )

        return report, sha256

    async def _get_or_create_dictionary(
        self, dict_input, dry_run: bool
    ) -> Tuple[DictionaryReport, Dictionary]:
        """Get existing dictionary or create new one.

        Args:
            dict_input: Dictionary metadata from import.
            dry_run: If True, don't actually create.

        Returns:
            Tuple of (report, dictionary).
        """
        from sqlalchemy import select

        # Check if dictionary exists
        result = await self.session.execute(
            select(Dictionary).where(Dictionary.code == dict_input.code)
        )
        dictionary = result.scalar_one_or_none()

        if dictionary:
            # Dictionary exists — don't change is_general
            return DictionaryReport(
                code=dictionary.code,
                name=dictionary.name,
                created=False,
            ), dictionary

        # Check if creating general dictionary would violate constraint
        if dict_input.is_general:
            result = await self.session.execute(
                select(Dictionary).where(Dictionary.is_general == True)
            )
            if result.scalar_one_or_none():
                raise ValueError("Cannot create another general dictionary")

        # Create new dictionary
        if not dry_run:
            dictionary = Dictionary(
                code=dict_input.code,
                name=dict_input.name,
                description=dict_input.description,
                is_general=dict_input.is_general,
            )
            self.session.add(dictionary)
            await self.session.flush()

        return DictionaryReport(
            code=dict_input.code,
            name=dict_input.name,
            created=True,
        ), dictionary

    def _validate_words(
        self, words: list, require_level: bool
    ) -> Tuple[List[dict], List[ErrorDetail]]:
        """Validate words and separate valid from invalid.

        Args:
            words: List of word inputs.
            require_level: If True, level is required (for general dictionary).

        Returns:
            Tuple of (valid_words, error_details).
        """
        valid_words = []
        error_details = []
        seen_keys = set()

        for idx, word in enumerate(words):
            errors = []

            # Validate lemma
            lemma = word.lemma.strip()
            lemma = unicodedata.normalize("NFC", lemma)

            if len(lemma) < 1 or len(lemma) > 64:
                errors.append(ErrorDetail(
                    index=idx,
                    lemma=word.lemma,
                    pos=word.pos,
                    code="lemma_too_long" if len(lemma) > 64 else "invalid_lemma",
                    message=f"Lemma length must be 1-64, got {len(lemma)}",
                ))

            if not lemma or not all(c.isalpha() or c in "'- " for c in lemma):
                errors.append(ErrorDetail(
                    index=idx,
                    lemma=word.lemma,
                    pos=word.pos,
                    code="invalid_lemma",
                    message="Lemma contains invalid characters",
                ))

            # Validate POS
            if word.pos not in VALID_POS:
                errors.append(ErrorDetail(
                    index=idx,
                    lemma=word.lemma,
                    pos=word.pos,
                    code="invalid_pos",
                    message=f"Invalid POS: {word.pos}",
                ))

            # Validate level
            if word.level is not None and word.level not in VALID_LEVELS:
                errors.append(ErrorDetail(
                    index=idx,
                    lemma=word.lemma,
                    pos=word.pos,
                    code="invalid_level",
                    message=f"Invalid level: {word.level}",
                ))

            if require_level and word.level is None:
                errors.append(ErrorDetail(
                    index=idx,
                    lemma=word.lemma,
                    pos=word.pos,
                    code="level_required",
                    message="Level is required for general dictionary",
                ))

            # Validate translations
            if not word.translations:
                errors.append(ErrorDetail(
                    index=idx,
                    lemma=word.lemma,
                    pos=word.pos,
                    code="empty_translations",
                    message="No translations provided",
                ))

            # Check for duplicates within file
            lemma_key = normalize_lemma(lemma)
            word_key = (lemma_key, word.pos)

            if word_key in seen_keys:
                errors.append(ErrorDetail(
                    index=idx,
                    lemma=word.lemma,
                    pos=word.pos,
                    code="duplicate_in_file",
                    message="Duplicate word in file",
                ))
            else:
                seen_keys.add(word_key)

            if errors:
                error_details.extend(errors)
            else:
                valid_words.append({
                    "lemma": lemma,
                    "lemma_key": lemma_key,
                    "pos": word.pos,
                    "level": word.level,
                    "translations": word.translations,
                })

        return valid_words, error_details

    async def _apply_import(
        self,
        admin_id: int,
        file_name: str,
        sha256: str,
        dictionary: Dictionary,
        valid_words: List[dict],
        error_details: List[ErrorDetail],
    ) -> ImportReport:
        """Apply import with advisory lock and batch processing.

        Args:
            admin_id: Admin user ID.
            file_name: Name of the file.
            sha256: SHA256 hash of the file.
            dictionary: Target dictionary.
            valid_words: List of validated words.
            error_details: List of validation errors.

        Returns:
            Import report.
        """
        from app.models.dictionary_import import DictionaryImport

        # Acquire advisory lock based on dictionary code hash
        lock_id = hash(dictionary.code) & 0x7FFFFFFF  # 31-bit positive integer
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_id)"),
            {"lock_id": lock_id},
        )

        added = 0
        linked = 0
        skipped = 0
        already_in_dictionary = 0

        # Process words in batches
        batch_size = 1000
        for i in range(0, len(valid_words), batch_size):
            batch = valid_words[i:i + batch_size]

            # Insert words with ON CONFLICT DO NOTHING
            for word_data in batch:
                # Try to insert word
                result = await self.session.execute(
                    text("""
                        INSERT INTO words (lemma, lemma_key, pos, level, translations)
                        VALUES (:lemma, :lemma_key, :pos, :level, :translations)
                        ON CONFLICT (lemma_key, pos) DO NOTHING
                        RETURNING id
                    """),
                    {
                        "lemma": word_data["lemma"],
                        "lemma_key": word_data["lemma_key"],
                        "pos": word_data["pos"],
                        "level": word_data["level"],
                        "translations": word_data["translations"],
                    },
                )

                word_id_result = result.scalar_one_or_none()

                if word_id_result:
                    # New word was inserted
                    added += 1
                    word_id = word_id_result
                else:
                    # Word already exists — get its ID
                    from sqlalchemy import select
                    from app.models.word import Word

                    result = await self.session.execute(
                        select(Word.id).where(
                            Word.lemma_key == word_data["lemma_key"],
                            Word.pos == word_data["pos"],
                        )
                    )
                    word_id = result.scalar_one()

                # Link word to dictionary
                result = await self.session.execute(
                    text("""
                        INSERT INTO dictionary_words (dictionary_id, word_id)
                        VALUES (:dict_id, :word_id)
                        ON CONFLICT DO NOTHING
                    """),
                    {"dict_id": dictionary.id, "word_id": word_id},
                )

                if result.rowcount > 0:
                    linked += 1
                else:
                    already_in_dictionary += 1
                    error_details.append(ErrorDetail(
                        index=-1,
                        lemma=word_data["lemma"],
                        pos=word_data["pos"],
                        code="already_in_dictionary",
                        message="Word already in dictionary",
                    ))

        # Record import
        import_record = DictionaryImport(
            admin_id=admin_id,
            file_name=file_name,
            sha256=sha256,
            dictionary_id=dictionary.id,
            added_count=added,
            linked_count=linked,
            skipped_count=len(error_details),
            errors_count=len(error_details),
            dry_run=False,
            report={
                "added": added,
                "linked": linked,
                "skipped": skipped,
                "errors": len(error_details),
            },
        )
        self.session.add(import_record)
        await self.session.flush()

        return ImportReport(
            dictionary=DictionaryReport(
                code=dictionary.code,
                name=dictionary.name,
                created=False,  # We don't track this in apply
            ),
            added=added,
            linked=linked,
            skipped=skipped,
            errors=len(error_details),
            error_details=error_details[:200],
        )
