class Database:
    def __init__(self, database_url):
        self.database_url = database_url
        self.pool = None

    async def connect(self):
        import asyncpg
        self.pool = await asyncpg.create_pool(self.database_url)

    async def close(self):
        await self.pool.close()

    async def create_user(self, username, email, phone_number, google_id, apple_id):
        query = """
        INSERT INTO users (username, email, phone_number, google_id, apple_id)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id;
        """
        return await self.pool.fetchval(query, username, email, phone_number, google_id, apple_id)

    async def get_user(self, user_id):
        query = """
        SELECT id, username, email, phone_number, google_id, apple_id
        FROM users
        WHERE id = $1;
        """
        return await self.pool.fetchrow(query, int(user_id))

    async def create_or_update_user(self, username, email, phone_number, google_id, apple_id):
        username = username or ""
        email = email or ""
        phone_number = phone_number or ""
        google_id = google_id or ""
        apple_id = apple_id or ""

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # 1) find existing by any identifier that is present
                row = await conn.fetchrow("""
                    SELECT id FROM users
                    WHERE ($1 <> '' AND google_id = $1)
                       OR ($2 <> '' AND apple_id  = $2)
                       OR ($3 <> '' AND email     = $3)
                       OR ($4 <> '' AND phone_number = $4)
                       OR ($5 <> '' AND username  = $5)
                    LIMIT 1
                """, google_id, apple_id, email, phone_number, username)

                if row:
                    user_id = row["id"]
                    # 2) update only non-empty fields
                    await conn.execute("""
                        UPDATE users SET
                            username     = COALESCE(NULLIF($1, ''), username),
                            email        = COALESCE(NULLIF($2, ''), email),
                            phone_number = COALESCE(NULLIF($3, ''), phone_number),
                            google_id    = COALESCE(NULLIF($4, ''), google_id),
                            apple_id     = COALESCE(NULLIF($5, ''), apple_id),
                            updated_at   = now()
                        WHERE id = $6
                    """, username, email, phone_number, google_id, apple_id, user_id)
                    return user_id

                # 3) insert new
                user_id = await conn.fetchval("""
                    INSERT INTO users (username, email, phone_number, google_id, apple_id)
                    VALUES (NULLIF($1,''), NULLIF($2,''), NULLIF($3,''), NULLIF($4,''), NULLIF($5,''))
                    RETURNING id
                """, username, email, phone_number, google_id, apple_id)
                return user_id
