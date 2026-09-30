"""Service for admin database browser (read-only)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import AppException
from app.schemas.admin_db import ColumnInfo, TableDataResponse, TableInfo

logger = logging.getLogger(__name__)

# Sensitive columns that must be masked
SENSITIVE_COLUMNS: Set[Tuple[str, str]] = {
    ("users", "password_hash"),
    ("refresh_tokens", "token_hash"),
}

# Technical tables to exclude from listing
EXCLUDED_TABLES: Set[str] = {
    "alembic_version",
}


class AdminDbService:
    """Read-only database browser service for admins."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_tables(self) -> List[TableInfo]:
        """
        Get list of all user tables with approximate row counts.
        
        Uses pg_class.reltuples for fast approximate counts.
        Excludes technical tables like alembic_version.
        """
        query = """
            SELECT 
                t.table_name,
                COALESCE(c.reltuples, 0)::bigint AS row_count_estimate,
                COUNT(col.column_name)::int AS columns_count
            FROM information_schema.tables t
            LEFT JOIN pg_class c ON c.relname = t.table_name
            LEFT JOIN information_schema.columns col 
                ON col.table_name = t.table_name 
                AND col.table_schema = t.table_schema
            WHERE t.table_schema = 'public'
                AND t.table_type = 'BASE TABLE'
                AND t.table_name NOT IN :excluded_tables
            GROUP BY t.table_name, c.reltuples
            ORDER BY t.table_name
        """
        
        result = await self.session.execute(
            text(query),
            {"excluded_tables": tuple(EXCLUDED_TABLES)}
        )
        
        tables = []
        for row in result:
            tables.append(TableInfo(
                table_name=row.table_name,
                row_count_estimate=max(0, int(row.row_count_estimate)),
                columns_count=row.columns_count,
            ))
        
        return tables

    async def get_table_data(
        self,
        table_name: str,
        page: int = 1,
        page_size: int = 25,
        order_by: Optional[str] = None,
        order_dir: str = "asc",
        search: Optional[str] = None,
    ) -> TableDataResponse:
        """
        Get paginated table data with optional sorting and search.
        
        All identifiers are safely escaped using psycopg.sql.Identifier.
        Sensitive columns are masked at SQL level.
        """
        # Validate table exists
        if not await self._validate_table(table_name):
            raise AppException(
                status_code=404,
                code="table_not_found",
                message=f"Table '{table_name}' not found",
            )
        
        # Validate page_size
        if page_size < 1 or page_size > 100:
            raise AppException(
                status_code=422,
                code="invalid_page_size",
                message="page_size must be between 1 and 100",
            )
        
        # Get columns
        columns = await self._get_columns(table_name)
        column_names = [col.name for col in columns]
        
        # Validate order_by
        if order_by:
            if order_by not in column_names:
                raise AppException(
                    status_code=422,
                    code="invalid_order_by",
                    message=f"Column '{order_by}' does not exist in table '{table_name}'",
                )
        else:
            # Default to primary key or first column
            pk_columns = [col.name for col in columns if col.is_primary_key]
            order_by = pk_columns[0] if pk_columns else column_names[0]
        
        # Validate order_dir
        if order_dir not in ("asc", "desc"):
            raise AppException(
                status_code=422,
                code="invalid_order_dir",
                message="order_dir must be 'asc' or 'desc'",
            )
        
        # Build and execute query
        rows, total = await self._execute_table_query(
            table_name=table_name,
            columns=columns,
            page=page,
            page_size=page_size,
            order_by=order_by,
            order_dir=order_dir,
            search=search,
        )
        
        return TableDataResponse(
            table_name=table_name,
            columns=columns,
            rows=rows,
            page=page,
            page_size=page_size,
            total=total,
        )

    async def _validate_table(self, table_name: str) -> bool:
        """Check if table exists in public schema."""
        query = """
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                    AND table_type = 'BASE TABLE'
                    AND table_name = :table_name
            )
        """
        result = await self.session.execute(text(query), {"table_name": table_name})
        return result.scalar() or False

    async def _get_columns(self, table_name: str) -> List[ColumnInfo]:
        """Get column information with primary key and masking flags."""
        # Get columns
        query = """
            SELECT 
                c.column_name,
                c.data_type,
                CASE 
                    WHEN kcu.column_name IS NOT NULL THEN true 
                    ELSE false 
                END AS is_primary_key
            FROM information_schema.columns c
            LEFT JOIN information_schema.key_column_usage kcu
                ON kcu.table_name = c.table_name
                AND kcu.table_schema = c.table_schema
                AND kcu.column_name = c.column_name
                AND kcu.constraint_name IN (
                    SELECT tc.constraint_name
                    FROM information_schema.table_constraints tc
                    WHERE tc.table_name = c.table_name
                        AND tc.table_schema = c.table_schema
                        AND tc.constraint_type = 'PRIMARY KEY'
                )
            WHERE c.table_schema = 'public'
                AND c.table_name = :table_name
            ORDER BY c.ordinal_position
        """
        
        result = await self.session.execute(text(query), {"table_name": table_name})
        
        columns = []
        for row in result:
            is_masked = (table_name, row.column_name) in SENSITIVE_COLUMNS
            columns.append(ColumnInfo(
                name=row.column_name,
                type=row.data_type,
                is_primary_key=row.is_primary_key,
                masked=is_masked,
            ))
        
        return columns

    async def _execute_table_query(
        self,
        table_name: str,
        columns: List[ColumnInfo],
        page: int,
        page_size: int,
        order_by: str,
        order_dir: str,
        search: Optional[str],
    ) -> Tuple[List[Dict[str, Any]], Optional[int]]:
        """
        Execute table query with safe identifier handling.
        
        Uses psycopg.sql for safe identifier escaping.
        """
        from psycopg import sql
        
        # Build SELECT clause with masking
        select_parts = []
        for col in columns:
            col_ident = sql.Identifier(col.name)
            if col.masked:
                # Mask sensitive columns
                select_parts.append(
                    sql.SQL("'••••••••' AS {}").format(col_ident)
                )
            else:
                select_parts.append(col_ident)
        
        select_clause = sql.SQL(", ").join(select_parts)
        table_ident = sql.Identifier(table_name)
        order_ident = sql.Identifier(order_by)
        order_dir_sql = sql.SQL("ASC") if order_dir == "asc" else sql.SQL("DESC")
        
        # Build WHERE clause for search
        where_clause = sql.SQL("")
        params = {}
        
        if search:
            # Search in all text columns
            text_columns = [
                col for col in columns 
                if col.type in ("text", "character varying", "varchar", "character", "char")
                and not col.masked
            ]
            
            if text_columns:
                search_conditions = []
                for col in text_columns:
                    col_ident = sql.Identifier(col.name)
                    search_conditions.append(
                        sql.SQL("{} ILIKE :search_pattern").format(col_ident)
                    )
                
                where_clause = sql.SQL(" WHERE ") + sql.SQL(" OR ").join(search_conditions)
                params["search_pattern"] = f"%{search}%"
        
        # Build ORDER BY and LIMIT/OFFSET
        offset = (page - 1) * page_size
        params["limit"] = page_size
        params["offset"] = offset
        
        # Main query
        query = sql.SQL(
            "SELECT {select} FROM {table}{where} ORDER BY {order} {dir} LIMIT :limit OFFSET :offset"
        ).format(
            select=select_clause,
            table=table_ident,
            where=where_clause,
            order=order_ident,
            dir=order_dir_sql,
        )
        
        # Execute main query
        result = await self.session.execute(query, params)
        rows = [dict(row._mapping) for row in result]
        
        # Get total count with timeout
        total = await self._get_total_count(
            table_name=table_name,
            columns=columns,
            search=search,
        )
        
        return rows, total

    async def _get_total_count(
        self,
        table_name: str,
        columns: List[ColumnInfo],
        search: Optional[str],
    ) -> Optional[int]:
        """
        Get total row count with 5 second timeout.
        
        Returns None if timeout exceeded.
        """
        from psycopg import sql
        
        table_ident = sql.Identifier(table_name)
        
        # Build WHERE clause for search
        where_clause = sql.SQL("")
        params = {}
        
        if search:
            text_columns = [
                col for col in columns 
                if col.type in ("text", "character varying", "varchar", "character", "char")
                and not col.masked
            ]
            
            if text_columns:
                search_conditions = []
                for col in text_columns:
                    col_ident = sql.Identifier(col.name)
                    search_conditions.append(
                        sql.SQL("{} ILIKE :search_pattern").format(col_ident)
                    )
                
                where_clause = sql.SQL(" WHERE ") + sql.SQL(" OR ").join(search_conditions)
                params["search_pattern"] = f"%{search}%"
        
        # Count query
        query = sql.SQL("SELECT COUNT(*) FROM {table}{where}").format(
            table=table_ident,
            where=where_clause,
        )
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                self.session.execute(query, params),
                timeout=5.0,
            )
            return result.scalar()
        except asyncio.TimeoutError:
            logger.warning(f"Count query timeout for table {table_name}")
            return None
        except Exception as e:
            logger.error(f"Error counting rows: {e}")
            return None
