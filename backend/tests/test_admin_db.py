"""Tests for admin database browser service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.exceptions import AppException
from app.schemas.admin_db import ColumnInfo, TableInfo
from app.services.admin_db_service import AdminDbService


class TestAdminDbService:
    """Tests for AdminDbService."""

    @pytest.mark.asyncio
    async def test_get_tables(self):
        """Should return list of tables with row counts."""
        session = AsyncMock()
        
        # Mock query result
        mock_row = MagicMock()
        mock_row.table_name = "users"
        mock_row.row_count_estimate = 120
        mock_row.columns_count = 8
        
        session.execute = AsyncMock()
        session.execute.return_value = [mock_row]
        
        service = AdminDbService(session)
        result = await service.get_tables()
        
        assert len(result) == 1
        assert result[0].table_name == "users"
        assert result[0].row_count_estimate == 120
        assert result[0].columns_count == 8

    @pytest.mark.asyncio
    async def test_get_table_data_success(self):
        """Should return table data with pagination."""
        session = AsyncMock()
        
        # Mock validate_table
        mock_exists = MagicMock()
        mock_exists.scalar.return_value = True
        
        # Mock get_columns
        mock_columns = [
            MagicMock(
                column_name="id",
                data_type="integer",
                is_primary_key=True,
            ),
            MagicMock(
                column_name="email",
                data_type="character varying",
                is_primary_key=False,
            ),
        ]
        
        # Mock execute_table_query
        mock_rows = [{"id": 1, "email": "test@example.com"}]
        mock_total = 100
        
        session.execute = AsyncMock()
        session.execute.side_effect = [
            mock_exists,  # validate_table
            mock_columns,  # get_columns
            (mock_rows, mock_total),  # execute_table_query
        ]
        
        service = AdminDbService(session)
        
        # Mock internal methods
        service._validate_table = AsyncMock(return_value=True)
        service._get_columns = AsyncMock(return_value=[
            ColumnInfo(name="id", type="integer", is_primary_key=True, masked=False),
            ColumnInfo(name="email", type="character varying", is_primary_key=False, masked=False),
        ])
        service._execute_table_query = AsyncMock(return_value=(mock_rows, mock_total))
        
        result = await service.get_table_data(
            table_name="users",
            page=1,
            page_size=25,
        )
        
        assert result.table_name == "users"
        assert len(result.columns) == 2
        assert len(result.rows) == 1
        assert result.total == 100

    @pytest.mark.asyncio
    async def test_get_table_data_not_found(self):
        """Should raise 404 if table not found."""
        session = AsyncMock()
        
        service = AdminDbService(session)
        service._validate_table = AsyncMock(return_value=False)
        
        with pytest.raises(AppException) as exc_info:
            await service.get_table_data(table_name="nonexistent")
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.code == "table_not_found"

    @pytest.mark.asyncio
    async def test_get_table_data_invalid_page_size(self):
        """Should raise 422 if page_size out of range."""
        session = AsyncMock()
        
        service = AdminDbService(session)
        service._validate_table = AsyncMock(return_value=True)
        
        with pytest.raises(AppException) as exc_info:
            await service.get_table_data(
                table_name="users",
                page_size=200,  # > 100
            )
        
        assert exc_info.value.status_code == 422
        assert exc_info.value.code == "invalid_page_size"

    @pytest.mark.asyncio
    async def test_get_table_data_invalid_order_by(self):
        """Should raise 422 if order_by column doesn't exist."""
        session = AsyncMock()
        
        service = AdminDbService(session)
        service._validate_table = AsyncMock(return_value=True)
        service._get_columns = AsyncMock(return_value=[
            ColumnInfo(name="id", type="integer", is_primary_key=True, masked=False),
        ])
        
        with pytest.raises(AppException) as exc_info:
            await service.get_table_data(
                table_name="users",
                order_by="nonexistent_column",
            )
        
        assert exc_info.value.status_code == 422
        assert exc_info.value.code == "invalid_order_by"

    @pytest.mark.asyncio
    async def test_get_table_data_invalid_order_dir(self):
        """Should raise 422 if order_dir is invalid."""
        session = AsyncMock()
        
        service = AdminDbService(session)
        service._validate_table = AsyncMock(return_value=True)
        service._get_columns = AsyncMock(return_value=[
            ColumnInfo(name="id", type="integer", is_primary_key=True, masked=False),
        ])
        
        with pytest.raises(AppException) as exc_info:
            await service.get_table_data(
                table_name="users",
                order_dir="invalid",
            )
        
        assert exc_info.value.status_code == 422
        assert exc_info.value.code == "invalid_order_dir"

    def test_sensitive_columns_masked(self):
        """Should identify sensitive columns for masking."""
        from app.services.admin_db_service import SENSITIVE_COLUMNS
        
        assert ("users", "password_hash") in SENSITIVE_COLUMNS
        assert ("refresh_tokens", "token_hash") in SENSITIVE_COLUMNS
        assert ("users", "email") not in SENSITIVE_COLUMNS

    def test_excluded_tables(self):
        """Should exclude technical tables."""
        from app.services.admin_db_service import EXCLUDED_TABLES
        
        assert "alembic_version" in EXCLUDED_TABLES
        assert "users" not in EXCLUDED_TABLES
