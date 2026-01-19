"""Pytest configuration and shared fixtures for User Service tests."""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from services.user_service import UserService
from db.database import IdentityCollisionError, ProfileLimitError, ProfileNameExistsError
from utils.grpc_errors import GrpcAbortException


class MockContext:
    """Mock gRPC context for testing."""

    def __init__(self):
        self.code = None
        self.details = None
        self._aborted = False

    def set_code(self, code):
        self.code = code

    def set_details(self, details):
        self.details = details

    def abort_with_status(self, status):
        """Handle structured error abort."""
        self._aborted = True
        # Extract code from status - status is a grpc.Status object
        self.code = status.code
        self.details = status.details
        raise GrpcAbortException()


class MockDatabase:
    """Mock database for testing without real PostgreSQL connection."""

    MAX_PROFILES_PER_USER = 5

    def __init__(self):
        self.users: dict[int, dict] = {}
        self.profiles: dict[int, dict] = {}
        self._next_user_id = 1
        self._next_profile_id = 1
        self.should_raise: Exception | None = None

    # ============ User Methods ============

    async def create_or_update_user(
        self,
        username: str | None,
        email: str | None,
        phone_number: str | None,
        google_id: str | None,
        apple_id: str | None,
    ) -> int:
        if self.should_raise:
            raise self.should_raise

        # Find all matching users (for collision detection)
        matching_user_ids = set()
        for user_id, user in self.users.items():
            if google_id and user.get("google_id") == google_id:
                matching_user_ids.add(user_id)
            if apple_id and user.get("apple_id") == apple_id:
                matching_user_ids.add(user_id)
            if email and user.get("email") == email:
                matching_user_ids.add(user_id)
            if phone_number and user.get("phone_number") == phone_number:
                matching_user_ids.add(user_id)
            if username and user.get("username") == username:
                matching_user_ids.add(user_id)

        # Check for identity collision
        if len(matching_user_ids) > 1:
            raise IdentityCollisionError(
                f"Identifiers match multiple existing users: {list(matching_user_ids)}"
            )

        if matching_user_ids:
            user_id = matching_user_ids.pop()
            self._update_user(user_id, username, email, phone_number, google_id, apple_id)
            return user_id

        # Create new user
        user_id = self._next_user_id
        self._next_user_id += 1
        self.users[user_id] = {
            "id": user_id,
            "username": username or "",
            "email": email or "",
            "phone_number": phone_number or "",
            "google_id": google_id or "",
            "apple_id": apple_id or "",
        }
        return user_id

    def _update_user(
        self,
        user_id: int,
        username: str | None,
        email: str | None,
        phone_number: str | None,
        google_id: str | None,
        apple_id: str | None,
    ) -> None:
        user = self.users[user_id]
        if username:
            user["username"] = username
        if email:
            user["email"] = email
        if phone_number:
            user["phone_number"] = phone_number
        if google_id:
            user["google_id"] = google_id
        if apple_id:
            user["apple_id"] = apple_id

    async def get_user(self, user_id: int) -> dict | None:
        if self.should_raise:
            raise self.should_raise
        return self.users.get(user_id)

    def add_user(self, **kwargs) -> int:
        """Helper to seed test data."""
        user_id = kwargs.get("id", self._next_user_id)
        if "id" not in kwargs:
            self._next_user_id += 1
        else:
            self._next_user_id = max(self._next_user_id, user_id + 1)

        self.users[user_id] = {
            "id": user_id,
            "username": kwargs.get("username", ""),
            "email": kwargs.get("email", ""),
            "phone_number": kwargs.get("phone_number", ""),
            "google_id": kwargs.get("google_id", ""),
            "apple_id": kwargs.get("apple_id", ""),
        }
        return user_id

    # ============ Profile Methods ============

    async def list_profiles(self, user_id: int) -> list[dict]:
        if self.should_raise:
            raise self.should_raise
        return [p for p in self.profiles.values() if p["user_id"] == user_id]

    async def create_profile(
        self,
        user_id: int,
        name: str,
        is_kids: bool = False,
        avatar: str = "",
        language: str = "uz",
        maturity_level: str = "all",
    ) -> dict:
        if self.should_raise:
            raise self.should_raise

        # Check profile count
        user_profiles = [p for p in self.profiles.values() if p["user_id"] == user_id]
        if len(user_profiles) >= self.MAX_PROFILES_PER_USER:
            raise ProfileLimitError(f"User {user_id} already has {len(user_profiles)} profiles")

        # Check for duplicate name
        for p in user_profiles:
            if p["name"] == name:
                raise ProfileNameExistsError(f"Profile name '{name}' already exists")

        profile_id = self._next_profile_id
        self._next_profile_id += 1
        profile = {
            "id": profile_id,
            "user_id": user_id,
            "name": name,
            "is_kids": is_kids,
            "avatar": avatar,
            "language": language,
            "maturity_level": maturity_level,
            "preferences": "[]",
            "created_at": None,
            "updated_at": None,
        }
        self.profiles[profile_id] = profile
        return profile

    async def get_profile(self, profile_id: int) -> dict | None:
        if self.should_raise:
            raise self.should_raise
        return self.profiles.get(profile_id)

    async def update_profile(
        self,
        profile_id: int,
        name: str | None = None,
        is_kids: bool | None = None,
        avatar: str | None = None,
        language: str | None = None,
        maturity_level: str | None = None,
        preferences: str | None = None,
    ) -> dict | None:
        if self.should_raise:
            raise self.should_raise

        profile = self.profiles.get(profile_id)
        if not profile:
            return None

        # Check name uniqueness
        if name is not None and name != profile["name"]:
            for p in self.profiles.values():
                if p["user_id"] == profile["user_id"] and p["name"] == name and p["id"] != profile_id:
                    raise ProfileNameExistsError(f"Profile name '{name}' already exists")

        if name is not None:
            profile["name"] = name
        if is_kids is not None:
            profile["is_kids"] = is_kids
        if avatar is not None:
            profile["avatar"] = avatar
        if language is not None:
            profile["language"] = language
        if maturity_level is not None:
            profile["maturity_level"] = maturity_level
        if preferences is not None:
            profile["preferences"] = preferences

        return profile

    async def delete_profile(self, profile_id: int) -> bool:
        if self.should_raise:
            raise self.should_raise
        if profile_id in self.profiles:
            del self.profiles[profile_id]
            return True
        return False

    def add_profile(self, **kwargs) -> int:
        """Helper to seed test profile data."""
        profile_id = kwargs.get("id", self._next_profile_id)
        if "id" not in kwargs:
            self._next_profile_id += 1
        else:
            self._next_profile_id = max(self._next_profile_id, profile_id + 1)

        self.profiles[profile_id] = {
            "id": profile_id,
            "user_id": kwargs.get("user_id", 1),
            "name": kwargs.get("name", "Profile"),
            "is_kids": kwargs.get("is_kids", False),
            "avatar": kwargs.get("avatar", ""),
            "language": kwargs.get("language", "uz"),
            "maturity_level": kwargs.get("maturity_level", "all"),
            "preferences": kwargs.get("preferences", "[]"),
            "created_at": None,
            "updated_at": None,
        }
        return profile_id


@pytest.fixture
def mock_db():
    return MockDatabase()


@pytest.fixture
def mock_context():
    return MockContext()


@pytest.fixture
def user_service(mock_db):
    return UserService(mock_db)
