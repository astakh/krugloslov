"""Tests for admin management services."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.exceptions import AppException
from app.models import RefreshToken, SentenceReport, User
from app.services.admin_reports_service import AdminReportsService
from app.services.admin_users_service import AdminUsersService


class TestAdminReportsService:
    """Tests for AdminReportsService."""

    @pytest.mark.asyncio
    async def test_get_reports_empty(self):
        """Should return empty list when no reports."""
        session = AsyncMock()
        admin = MagicMock(spec=User)
        admin.id = 1

        session.execute = AsyncMock()
        session.execute.return_value.scalar.return_value = 0
        session.execute.return_value.scalars.return_value.all.return_value = []

        service = AdminReportsService(session, admin)
        result = await service.get_reports()

        assert result.reports == []
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_process_report_success(self):
        """Should process report successfully."""
        session = AsyncMock()
        admin = MagicMock(spec=User)
        admin.id = 1

        # Mock report
        report = MagicMock(spec=SentenceReport)
        report.id = 1
        report.status = "new"
        report.admin_note = None

        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none.return_value = report
        session.commit = AsyncMock()

        service = AdminReportsService(session, admin)
        result = await service.process_report(
            report_id=1,
            status="processed",
            admin_note="Test note",
        )

        assert result == "Report processed successfully"
        assert report.status == "processed"
        assert report.admin_note == "Test note"
        session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_process_report_idempotent(self):
        """Should return success if already processed with same note."""
        session = AsyncMock()
        admin = MagicMock(spec=User)
        admin.id = 1

        # Mock report already processed
        report = MagicMock(spec=SentenceReport)
        report.id = 1
        report.status = "processed"
        report.admin_note = "Test note"

        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none.return_value = report

        service = AdminReportsService(session, admin)
        result = await service.process_report(
            report_id=1,
            status="processed",
            admin_note="Test note",
        )

        assert result == "Report already processed"

    @pytest.mark.asyncio
    async def test_process_report_not_found(self):
        """Should raise 404 if report not found."""
        session = AsyncMock()
        admin = MagicMock(spec=User)
        admin.id = 1

        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none.return_value = None

        service = AdminReportsService(session, admin)

        with pytest.raises(AppException) as exc_info:
            await service.process_report(report_id=999, status="processed")

        assert exc_info.value.status_code == 404
        assert exc_info.value.code == "report_not_found"


class TestAdminUsersService:
    """Tests for AdminUsersService."""

    @pytest.mark.asyncio
    async def test_get_users_empty(self):
        """Should return empty list when no users."""
        session = AsyncMock()
        admin = MagicMock(spec=User)
        admin.id = 1

        session.execute = AsyncMock()
        session.execute.return_value.scalar.return_value = 0
        session.execute.return_value.scalars.return_value.all.return_value = []

        service = AdminUsersService(session, admin)
        result = await service.get_users()

        assert result.users == []
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_reset_password_success(self):
        """Should reset password and revoke tokens."""
        session = AsyncMock()
        admin = MagicMock(spec=User)
        admin.id = 1

        # Mock target user
        target_user = MagicMock(spec=User)
        target_user.id = 2
        target_user.email = "user@example.com"

        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none.return_value = target_user
        session.commit = AsyncMock()

        service = AdminUsersService(session, admin)
        temp_password, message = await service.reset_password(user_id=2)

        assert len(temp_password) >= 12
        assert message == "Password reset successfully"
        session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_reset_password_user_not_found(self):
        """Should raise 404 if user not found."""
        session = AsyncMock()
        admin = MagicMock(spec=User)
        admin.id = 1

        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none.return_value = None

        service = AdminUsersService(session, admin)

        with pytest.raises(AppException) as exc_info:
            await service.reset_password(user_id=999)

        assert exc_info.value.status_code == 404
        assert exc_info.value.code == "user_not_found"

    @pytest.mark.asyncio
    async def test_reset_password_cannot_reset_own(self):
        """Should raise 400 if trying to reset own password."""
        session = AsyncMock()
        admin = MagicMock(spec=User)
        admin.id = 1

        # Mock admin as target user
        admin.id = 1
        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none.return_value = admin

        service = AdminUsersService(session, admin)

        with pytest.raises(AppException) as exc_info:
            await service.reset_password(user_id=1)

        assert exc_info.value.status_code == 400
        assert exc_info.value.code == "cannot_reset_own_password"

    def test_generate_temporary_password(self):
        """Should generate secure temporary password."""
        session = AsyncMock()
        admin = MagicMock(spec=User)
        admin.id = 1

        service = AdminUsersService(session, admin)
        password = service._generate_temporary_password()

        # Check length
        assert len(password) >= 12

        # Check contains at least one of each type
        assert any(c.isupper() for c in password)
        assert any(c.islower() for c in password)
        assert any(c.isdigit() for c in password)
        assert any(c in "!@#$%" for c in password)
