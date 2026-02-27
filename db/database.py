"""Database layer for user-service with asyncpg."""
from __future__ import annotations


# Maximum profiles per user
MAX_PROFILES_PER_USER = 5


class IdentityCollisionError(Exception):
    """Raised when identifiers match multiple different users."""
    pass


class ProfileLimitError(Exception):
    """Raised when user exceeds maximum profile count."""
    pass


class ProfileNameExistsError(Exception):
    """Raised when profile name already exists for user."""
    pass


class Database:
    def __init__(self, database_url):
        self.database_url = database_url
        self.pool = None

    async def connect(self):
        import asyncpg
        self.pool = await asyncpg.create_pool(self.database_url)

    async def close(self):
        await self.pool.close()

    # ============ User Methods ============

    async def create_user(self, username, email, phone_number, google_id, apple_id):
        query = """
        INSERT INTO users (username, email, phone_number, google_id, apple_id)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id;
        """
        return await self.pool.fetchval(query, username, email, phone_number, google_id, apple_id)

    async def get_user(self, user_id):
        query = """
        SELECT id, username, email, phone_number, google_id, apple_id, is_admin
        FROM users
        WHERE id = $1;
        """
        return await self.pool.fetchrow(query, int(user_id))

    async def create_or_update_user(self, username, email, phone_number, google_id, apple_id):
        """
        Create or update a user by any matching identifier.

        Returns:
            dict with user data including id, username, email, phone_number, google_id, apple_id, is_admin

        Raises:
            IdentityCollisionError: If identifiers match different existing users
        """
        username = username or ""
        email = email or ""
        phone_number = phone_number or ""
        google_id = google_id or ""
        apple_id = apple_id or ""

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Find ALL users matching ANY of the provided identifiers
                rows = await conn.fetch("""
                    SELECT DISTINCT id FROM users
                    WHERE ($1 <> '' AND google_id = $1)
                       OR ($2 <> '' AND apple_id  = $2)
                       OR ($3 <> '' AND email     = $3)
                       OR ($4 <> '' AND phone_number = $4)
                       OR ($5 <> '' AND username  = $5)
                """, google_id, apple_id, email, phone_number, username)

                # Check for identity collision
                if len(rows) > 1:
                    user_ids = [row["id"] for row in rows]
                    raise IdentityCollisionError(
                        f"Identifiers match multiple existing users: {user_ids}"
                    )

                if rows:
                    user_id = rows[0]["id"]
                    # Update only non-empty fields and return full user
                    user = await conn.fetchrow("""
                        UPDATE users SET
                            username     = COALESCE(NULLIF($1, ''), username),
                            email        = COALESCE(NULLIF($2, ''), email),
                            phone_number = COALESCE(NULLIF($3, ''), phone_number),
                            google_id    = COALESCE(NULLIF($4, ''), google_id),
                            apple_id     = COALESCE(NULLIF($5, ''), apple_id),
                            updated_at   = now()
                        WHERE id = $6
                        RETURNING id, username, email, phone_number, google_id, apple_id, is_admin
                    """, username, email, phone_number, google_id, apple_id, user_id)
                    return dict(user)

                # Insert new user and return full user
                user = await conn.fetchrow("""
                    INSERT INTO users (username, email, phone_number, google_id, apple_id, is_admin)
                    VALUES (NULLIF($1,''), NULLIF($2,''), NULLIF($3,''), NULLIF($4,''), NULLIF($5,''), false)
                    RETURNING id, username, email, phone_number, google_id, apple_id, is_admin
                """, username, email, phone_number, google_id, apple_id)
                return dict(user)

    async def list_users(self, page: int = 1, page_size: int = 10) -> dict:
        """List all users with pagination."""
        offset = (page - 1) * page_size

        async with self.pool.acquire() as conn:
            total = await conn.fetchval("SELECT COUNT(*) FROM users")

            rows = await conn.fetch("""
                SELECT id, username, email, phone_number, google_id, apple_id, is_admin
                FROM users
                ORDER BY id ASC
                LIMIT $1 OFFSET $2
            """, page_size, offset)

            return {
                "users": [dict(row) for row in rows],
                "total_count": total,
                "page": page,
                "total_pages": max(1, (total + page_size - 1) // page_size),
            }

    async def delete_user(self, user_id: int) -> bool:
        """Delete a user and all their profiles. Returns True if deleted, False if not found."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("DELETE FROM profiles WHERE user_id = $1", user_id)
                result = await conn.execute("DELETE FROM users WHERE id = $1", user_id)
                return result == "DELETE 1"

    # ============ Password Methods (admin only) ============

    async def set_password(self, user_id: int, password_hash: str):
        """Set password hash for a user."""
        await self.pool.execute(
            "UPDATE users SET password_hash = $1, updated_at = now() WHERE id = $2",
            password_hash, user_id
        )

    async def get_user_by_email_with_password(self, email: str) -> dict | None:
        """Get user by email including password_hash for verification."""
        row = await self.pool.fetchrow("""
            SELECT id, username, email, phone_number, google_id, apple_id,
                   is_admin, password_hash
            FROM users
            WHERE email = $1
        """, email)
        return dict(row) if row else None

    # ============ Profile Methods ============

    async def list_profiles(self, user_id: int) -> list[dict]:
        """List all profiles for a user."""
        query = """
            SELECT id, user_id, name, is_kids, avatar, language, maturity_level,
                   preferences::text, created_at, updated_at
            FROM profiles
            WHERE user_id = $1
            ORDER BY created_at ASC
        """
        rows = await self.pool.fetch(query, user_id)
        return [dict(row) for row in rows]

    async def create_profile(
        self,
        user_id: int,
        name: str,
        is_kids: bool = False,
        avatar: str = "",
        language: str = "uz",
        maturity_level: str = "all",
    ) -> dict:
        """
        Create a new profile for a user.

        Raises:
            ProfileLimitError: If user already has MAX_PROFILES_PER_USER profiles
            ProfileNameExistsError: If profile name already exists for this user
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Check profile count
                count = await conn.fetchval(
                    "SELECT COUNT(*) FROM profiles WHERE user_id = $1",
                    user_id
                )
                if count >= MAX_PROFILES_PER_USER:
                    raise ProfileLimitError(
                        f"User {user_id} already has {count} profiles (max: {MAX_PROFILES_PER_USER})"
                    )

                # Check for duplicate name
                existing = await conn.fetchval(
                    "SELECT id FROM profiles WHERE user_id = $1 AND name = $2",
                    user_id, name
                )
                if existing:
                    raise ProfileNameExistsError(
                        f"Profile name '{name}' already exists for user {user_id}"
                    )

                # Insert profile
                row = await conn.fetchrow("""
                    INSERT INTO profiles (user_id, name, is_kids, avatar, language, maturity_level, preferences)
                    VALUES ($1, $2, $3, $4, $5, $6, '[]'::jsonb)
                    RETURNING id, user_id, name, is_kids, avatar, language, maturity_level,
                              preferences::text, created_at, updated_at
                """, user_id, name, is_kids, avatar, language, maturity_level)
                return dict(row)

    async def get_profile(self, profile_id: int) -> dict | None:
        """Get a profile by ID."""
        query = """
            SELECT id, user_id, name, is_kids, avatar, language, maturity_level,
                   preferences::text, created_at, updated_at
            FROM profiles
            WHERE id = $1
        """
        row = await self.pool.fetchrow(query, profile_id)
        return dict(row) if row else None

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
        """
        Update a profile. Only non-None fields are updated.

        Raises:
            ProfileNameExistsError: If new name already exists for the user

        Returns:
            Updated profile dict, or None if profile not found
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Get current profile
                current = await conn.fetchrow(
                    "SELECT id, user_id, name FROM profiles WHERE id = $1",
                    profile_id
                )
                if not current:
                    return None

                # Check name uniqueness if name is being changed
                if name is not None and name != current["name"]:
                    existing = await conn.fetchval(
                        "SELECT id FROM profiles WHERE user_id = $1 AND name = $2 AND id != $3",
                        current["user_id"], name, profile_id
                    )
                    if existing:
                        raise ProfileNameExistsError(
                            f"Profile name '{name}' already exists for user {current['user_id']}"
                        )

                # Build dynamic update
                updates = []
                params = []
                param_idx = 1

                if name is not None:
                    updates.append(f"name = ${param_idx}")
                    params.append(name)
                    param_idx += 1
                if is_kids is not None:
                    updates.append(f"is_kids = ${param_idx}")
                    params.append(is_kids)
                    param_idx += 1
                if avatar is not None:
                    updates.append(f"avatar = ${param_idx}")
                    params.append(avatar)
                    param_idx += 1
                if language is not None:
                    updates.append(f"language = ${param_idx}")
                    params.append(language)
                    param_idx += 1
                if maturity_level is not None:
                    updates.append(f"maturity_level = ${param_idx}")
                    params.append(maturity_level)
                    param_idx += 1
                if preferences is not None:
                    updates.append(f"preferences = ${param_idx}::jsonb")
                    params.append(preferences)
                    param_idx += 1

                if not updates:
                    # No updates, return current
                    full_row = await conn.fetchrow("""
                        SELECT id, user_id, name, is_kids, avatar, language, maturity_level,
                               preferences::text, created_at, updated_at
                        FROM profiles WHERE id = $1
                    """, profile_id)
                    return dict(full_row)

                updates.append("updated_at = now()")
                params.append(profile_id)

                query = f"""
                    UPDATE profiles SET {', '.join(updates)}
                    WHERE id = ${param_idx}
                    RETURNING id, user_id, name, is_kids, avatar, language, maturity_level,
                              preferences::text, created_at, updated_at
                """
                row = await conn.fetchrow(query, *params)
                return dict(row) if row else None

    async def delete_profile(self, profile_id: int) -> bool:
        """Delete a profile. Returns True if deleted, False if not found."""
        result = await self.pool.execute(
            "DELETE FROM profiles WHERE id = $1",
            profile_id
        )
        # result is like "DELETE 1" or "DELETE 0"
        return result == "DELETE 1"
