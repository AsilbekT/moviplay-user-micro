"""gRPC service implementation for User Service."""
from __future__ import annotations

import grpc
import asyncpg
import logging

from proto import users_pb2, users_pb2_grpc
from utils.grpc_errors import abort, FieldViolation, ReasonCodes
from db.database import IdentityCollisionError, ProfileLimitError, ProfileNameExistsError

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class UserService(users_pb2_grpc.UserServiceServicer):
    def __init__(self, db):
        self.db = db

    # ============ User Operations ============

    async def CreateUser(self, request, context):
        logger.info(f"CreateUser called with: username={request.username}, email={request.email}, phone={request.phone_number}")
        try:
            # Validate: at least one identifier required
            has_identifier = any([
                request.username,
                request.email,
                request.phone_number,
                request.google_id,
                request.apple_id,
            ])
            if not has_identifier:
                await abort(
                    context,
                    grpc.StatusCode.INVALID_ARGUMENT,
                    ReasonCodes.INVALID_ARGUMENT,
                    "At least one identifier (email, phone_number, google_id, apple_id, or username) is required.",
                )

            user_id = await self.db.create_or_update_user(
                username=request.username if request.username else None,
                email=request.email if request.email else None,
                phone_number=request.phone_number if request.phone_number else None,
                google_id=request.google_id if request.google_id else None,
                apple_id=request.apple_id if request.apple_id else None,
            )
            return users_pb2.UserResponse(
                user_id=int(user_id),
                username=request.username,
                email=request.email,
                phone_number=request.phone_number,
                google_id=request.google_id,
                apple_id=request.apple_id,
            )

        except IdentityCollisionError:
            await abort(
                context,
                grpc.StatusCode.INVALID_ARGUMENT,
                ReasonCodes.IDENTITY_CONFLICT,
                "Provided identifiers match multiple existing users.",
            )

        except asyncpg.PostgresConnectionError:
            await abort(
                context,
                grpc.StatusCode.UNAVAILABLE,
                ReasonCodes.DB_UNAVAILABLE,
                "Database is temporarily unavailable.",
            )

        except asyncpg.QueryCanceledError:
            await abort(
                context,
                grpc.StatusCode.DEADLINE_EXCEEDED,
                ReasonCodes.DB_TIMEOUT,
                "Database request timed out.",
            )

        except Exception as e:
            logger.exception(f"CreateUser failed with exception: {e}")
            await abort(
                context,
                grpc.StatusCode.INTERNAL,
                ReasonCodes.INTERNAL_ERROR,
                "An internal error occurred.",
            )

    async def GetUser(self, request, context):
        try:
            # Validate user_id (int64 in proto)
            if request.user_id <= 0:
                await abort(
                    context,
                    grpc.StatusCode.INVALID_ARGUMENT,
                    ReasonCodes.INVALID_ID,
                    "Invalid user_id. Must be a positive integer.",
                    fields=[FieldViolation("user_id", "Must be greater than 0")],
                )

            user = await self.db.get_user(request.user_id)
            if not user:
                await abort(
                    context,
                    grpc.StatusCode.NOT_FOUND,
                    ReasonCodes.USER_NOT_FOUND,
                    f"User with ID {request.user_id} not found.",
                )

            return users_pb2.UserResponse(
                user_id=int(user["id"]),
                username=user["username"] if user["username"] else "",
                email=user["email"] if user["email"] else "",
                phone_number=user["phone_number"] if user["phone_number"] else "",
                google_id=user["google_id"] if user["google_id"] else "",
                apple_id=user["apple_id"] if user["apple_id"] else "",
            )

        except asyncpg.PostgresConnectionError:
            await abort(
                context,
                grpc.StatusCode.UNAVAILABLE,
                ReasonCodes.DB_UNAVAILABLE,
                "Database is temporarily unavailable.",
            )

        except asyncpg.QueryCanceledError:
            await abort(
                context,
                grpc.StatusCode.DEADLINE_EXCEEDED,
                ReasonCodes.DB_TIMEOUT,
                "Database request timed out.",
            )

        except Exception:
            await abort(
                context,
                grpc.StatusCode.INTERNAL,
                ReasonCodes.INTERNAL_ERROR,
                "An internal error occurred.",
            )

    # ============ Profile Operations ============

    async def ListProfiles(self, request, context):
        try:
            if request.user_id <= 0:
                await abort(
                    context,
                    grpc.StatusCode.INVALID_ARGUMENT,
                    ReasonCodes.INVALID_ID,
                    "Invalid user_id. Must be a positive integer.",
                    fields=[FieldViolation("user_id", "Must be greater than 0")],
                )

            profiles = await self.db.list_profiles(request.user_id)
            return users_pb2.ListProfilesResponse(
                profiles=[self._to_profile_proto(p) for p in profiles]
            )

        except asyncpg.PostgresConnectionError:
            await abort(
                context,
                grpc.StatusCode.UNAVAILABLE,
                ReasonCodes.DB_UNAVAILABLE,
                "Database is temporarily unavailable.",
            )

        except asyncpg.QueryCanceledError:
            await abort(
                context,
                grpc.StatusCode.DEADLINE_EXCEEDED,
                ReasonCodes.DB_TIMEOUT,
                "Database request timed out.",
            )

        except Exception as e:
            logger.exception(f"ListProfiles failed: {e}")
            await abort(
                context,
                grpc.StatusCode.INTERNAL,
                ReasonCodes.INTERNAL_ERROR,
                "An internal error occurred.",
            )

    async def CreateProfile(self, request, context):
        try:
            # Validate user_id
            if request.user_id <= 0:
                await abort(
                    context,
                    grpc.StatusCode.INVALID_ARGUMENT,
                    ReasonCodes.INVALID_ID,
                    "Invalid user_id. Must be a positive integer.",
                    fields=[FieldViolation("user_id", "Must be greater than 0")],
                )

            # Validate name
            name = request.name.strip()
            if not name or len(name) < 1 or len(name) > 50:
                await abort(
                    context,
                    grpc.StatusCode.INVALID_ARGUMENT,
                    ReasonCodes.INVALID_ARGUMENT,
                    "Profile name must be 1-50 characters.",
                    fields=[FieldViolation("name", "Must be 1-50 characters")],
                )

            profile = await self.db.create_profile(
                user_id=request.user_id,
                name=name,
                is_kids=request.is_kids,
                avatar=request.avatar or "",
                language=request.language or "uz",
                maturity_level=request.maturity_level or "all",
            )
            return users_pb2.ProfileResponse(profile=self._to_profile_proto(profile))

        except ProfileLimitError:
            await abort(
                context,
                grpc.StatusCode.FAILED_PRECONDITION,
                ReasonCodes.PROFILE_LIMIT_REACHED,
                "Maximum of 5 profiles per user reached.",
            )

        except ProfileNameExistsError:
            await abort(
                context,
                grpc.StatusCode.ALREADY_EXISTS,
                ReasonCodes.PROFILE_NAME_EXISTS,
                f"Profile name '{request.name}' already exists for this user.",
                fields=[FieldViolation("name", "Name already in use")],
            )

        except asyncpg.PostgresConnectionError:
            await abort(
                context,
                grpc.StatusCode.UNAVAILABLE,
                ReasonCodes.DB_UNAVAILABLE,
                "Database is temporarily unavailable.",
            )

        except asyncpg.QueryCanceledError:
            await abort(
                context,
                grpc.StatusCode.DEADLINE_EXCEEDED,
                ReasonCodes.DB_TIMEOUT,
                "Database request timed out.",
            )

        except Exception:
            await abort(
                context,
                grpc.StatusCode.INTERNAL,
                ReasonCodes.INTERNAL_ERROR,
                "An internal error occurred.",
            )

    async def GetProfile(self, request, context):
        try:
            if request.profile_id <= 0:
                await abort(
                    context,
                    grpc.StatusCode.INVALID_ARGUMENT,
                    ReasonCodes.INVALID_ID,
                    "Invalid profile_id. Must be a positive integer.",
                    fields=[FieldViolation("profile_id", "Must be greater than 0")],
                )

            profile = await self.db.get_profile(request.profile_id)
            if not profile:
                await abort(
                    context,
                    grpc.StatusCode.NOT_FOUND,
                    ReasonCodes.PROFILE_NOT_FOUND,
                    f"Profile with ID {request.profile_id} not found.",
                )

            return users_pb2.ProfileResponse(profile=self._to_profile_proto(profile))

        except asyncpg.PostgresConnectionError:
            await abort(
                context,
                grpc.StatusCode.UNAVAILABLE,
                ReasonCodes.DB_UNAVAILABLE,
                "Database is temporarily unavailable.",
            )

        except asyncpg.QueryCanceledError:
            await abort(
                context,
                grpc.StatusCode.DEADLINE_EXCEEDED,
                ReasonCodes.DB_TIMEOUT,
                "Database request timed out.",
            )

        except Exception:
            await abort(
                context,
                grpc.StatusCode.INTERNAL,
                ReasonCodes.INTERNAL_ERROR,
                "An internal error occurred.",
            )

    async def UpdateProfile(self, request, context):
        try:
            if request.profile_id <= 0:
                await abort(
                    context,
                    grpc.StatusCode.INVALID_ARGUMENT,
                    ReasonCodes.INVALID_ID,
                    "Invalid profile_id. Must be a positive integer.",
                    fields=[FieldViolation("profile_id", "Must be greater than 0")],
                )

            # Determine which fields to update based on update_mask
            update_mask = set(request.update_mask) if request.update_mask else None

            # Build update kwargs
            kwargs = {}
            if update_mask is None or "name" in update_mask:
                if request.name:
                    name = request.name.strip()
                    if len(name) < 1 or len(name) > 50:
                        await abort(
                            context,
                            grpc.StatusCode.INVALID_ARGUMENT,
                            ReasonCodes.INVALID_ARGUMENT,
                            "Profile name must be 1-50 characters.",
                            fields=[FieldViolation("name", "Must be 1-50 characters")],
                        )
                    kwargs["name"] = name

            if update_mask is None or "is_kids" in update_mask:
                kwargs["is_kids"] = request.is_kids
            if update_mask is None or "avatar" in update_mask:
                kwargs["avatar"] = request.avatar
            if update_mask is None or "language" in update_mask:
                kwargs["language"] = request.language
            if update_mask is None or "maturity_level" in update_mask:
                kwargs["maturity_level"] = request.maturity_level
            if update_mask is None or "preferences" in update_mask:
                kwargs["preferences"] = request.preferences if request.preferences else None

            profile = await self.db.update_profile(request.profile_id, **kwargs)
            if not profile:
                await abort(
                    context,
                    grpc.StatusCode.NOT_FOUND,
                    ReasonCodes.PROFILE_NOT_FOUND,
                    f"Profile with ID {request.profile_id} not found.",
                )

            return users_pb2.ProfileResponse(profile=self._to_profile_proto(profile))

        except ProfileNameExistsError:
            await abort(
                context,
                grpc.StatusCode.ALREADY_EXISTS,
                ReasonCodes.PROFILE_NAME_EXISTS,
                f"Profile name '{request.name}' already exists for this user.",
                fields=[FieldViolation("name", "Name already in use")],
            )

        except asyncpg.PostgresConnectionError:
            await abort(
                context,
                grpc.StatusCode.UNAVAILABLE,
                ReasonCodes.DB_UNAVAILABLE,
                "Database is temporarily unavailable.",
            )

        except asyncpg.QueryCanceledError:
            await abort(
                context,
                grpc.StatusCode.DEADLINE_EXCEEDED,
                ReasonCodes.DB_TIMEOUT,
                "Database request timed out.",
            )

        except Exception:
            await abort(
                context,
                grpc.StatusCode.INTERNAL,
                ReasonCodes.INTERNAL_ERROR,
                "An internal error occurred.",
            )

    async def DeleteProfile(self, request, context):
        try:
            if request.profile_id <= 0:
                await abort(
                    context,
                    grpc.StatusCode.INVALID_ARGUMENT,
                    ReasonCodes.INVALID_ID,
                    "Invalid profile_id. Must be a positive integer.",
                    fields=[FieldViolation("profile_id", "Must be greater than 0")],
                )

            deleted = await self.db.delete_profile(request.profile_id)
            if not deleted:
                await abort(
                    context,
                    grpc.StatusCode.NOT_FOUND,
                    ReasonCodes.PROFILE_NOT_FOUND,
                    f"Profile with ID {request.profile_id} not found.",
                )

            return users_pb2.DeleteProfileResponse(success=True)

        except asyncpg.PostgresConnectionError:
            await abort(
                context,
                grpc.StatusCode.UNAVAILABLE,
                ReasonCodes.DB_UNAVAILABLE,
                "Database is temporarily unavailable.",
            )

        except asyncpg.QueryCanceledError:
            await abort(
                context,
                grpc.StatusCode.DEADLINE_EXCEEDED,
                ReasonCodes.DB_TIMEOUT,
                "Database request timed out.",
            )

        except Exception:
            await abort(
                context,
                grpc.StatusCode.INTERNAL,
                ReasonCodes.INTERNAL_ERROR,
                "An internal error occurred.",
            )

    # ============ Helpers ============

    def _to_profile_proto(self, profile: dict) -> users_pb2.Profile:
        """Convert a profile dict to Profile protobuf message."""
        # Convert preferences string to bytes for proto
        prefs = profile["preferences"] or "[]"
        prefs_bytes = prefs.encode('utf-8') if isinstance(prefs, str) else prefs

        return users_pb2.Profile(
            id=int(profile["id"]),
            user_id=int(profile["user_id"]),
            name=profile["name"],
            is_kids=profile["is_kids"],
            avatar=profile["avatar"] or "",
            language=profile["language"] or "uz",
            maturity_level=profile["maturity_level"] or "all",
            preferences_json=prefs_bytes,
            created_at=profile["created_at"].isoformat() if profile.get("created_at") else "",
            updated_at=profile["updated_at"].isoformat() if profile.get("updated_at") else "",
        )
