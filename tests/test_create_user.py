"""Tests for CreateUser RPC."""
import pytest
import grpc

from proto import users_pb2
from utils.grpc_errors import GrpcAbortException


@pytest.mark.asyncio
async def test_create_user_with_email(user_service, mock_context):
    """New user created with email."""
    request = users_pb2.CreateUserRequest(email="test@example.com")

    response = await user_service.CreateUser(request, mock_context)

    assert response.user_id == "1"
    assert response.email == "test@example.com"
    assert mock_context.code is None


@pytest.mark.asyncio
async def test_create_user_with_phone(user_service, mock_context):
    """New user created with phone number."""
    request = users_pb2.CreateUserRequest(phone_number="+1234567890")

    response = await user_service.CreateUser(request, mock_context)

    assert response.user_id == "1"
    assert response.phone_number == "+1234567890"
    assert mock_context.code is None


@pytest.mark.asyncio
async def test_create_user_with_google_id(user_service, mock_context):
    """New user created with Google ID."""
    request = users_pb2.CreateUserRequest(google_id="google_123")

    response = await user_service.CreateUser(request, mock_context)

    assert response.user_id == "1"
    assert response.google_id == "google_123"
    assert mock_context.code is None


@pytest.mark.asyncio
async def test_create_user_with_apple_id(user_service, mock_context):
    """New user created with Apple ID."""
    request = users_pb2.CreateUserRequest(apple_id="apple_123")

    response = await user_service.CreateUser(request, mock_context)

    assert response.user_id == "1"
    assert response.apple_id == "apple_123"
    assert mock_context.code is None


@pytest.mark.asyncio
async def test_create_user_with_username(user_service, mock_context):
    """New user created with username."""
    request = users_pb2.CreateUserRequest(username="testuser")

    response = await user_service.CreateUser(request, mock_context)

    assert response.user_id == "1"
    assert response.username == "testuser"
    assert mock_context.code is None


@pytest.mark.asyncio
async def test_create_user_with_all_fields(user_service, mock_context):
    """New user created with all identifiers."""
    request = users_pb2.CreateUserRequest(
        username="testuser",
        email="test@example.com",
        phone_number="+1234567890",
        google_id="google_123",
        apple_id="apple_123",
    )

    response = await user_service.CreateUser(request, mock_context)

    assert response.user_id == "1"
    assert response.username == "testuser"
    assert response.email == "test@example.com"
    assert response.phone_number == "+1234567890"
    assert response.google_id == "google_123"
    assert response.apple_id == "apple_123"
    assert mock_context.code is None


@pytest.mark.asyncio
async def test_upsert_by_email(user_service, mock_db, mock_context):
    """Existing user updated when matched by email."""
    mock_db.add_user(id=1, email="test@example.com", username="olduser")

    request = users_pb2.CreateUserRequest(
        email="test@example.com",
        username="newuser",
    )

    response = await user_service.CreateUser(request, mock_context)

    assert response.user_id == "1"
    assert mock_db.users[1]["username"] == "newuser"
    assert mock_context.code is None


@pytest.mark.asyncio
async def test_upsert_by_google_id(user_service, mock_db, mock_context):
    """Existing user updated when matched by Google ID."""
    mock_db.add_user(id=1, google_id="google_123")

    request = users_pb2.CreateUserRequest(
        google_id="google_123",
        email="new@example.com",
    )

    response = await user_service.CreateUser(request, mock_context)

    assert response.user_id == "1"
    assert mock_db.users[1]["email"] == "new@example.com"
    assert mock_context.code is None


@pytest.mark.asyncio
async def test_upsert_by_apple_id(user_service, mock_db, mock_context):
    """Existing user updated when matched by Apple ID."""
    mock_db.add_user(id=1, apple_id="apple_123")

    request = users_pb2.CreateUserRequest(
        apple_id="apple_123",
        phone_number="+1234567890",
    )

    response = await user_service.CreateUser(request, mock_context)

    assert response.user_id == "1"
    assert mock_db.users[1]["phone_number"] == "+1234567890"
    assert mock_context.code is None


@pytest.mark.asyncio
async def test_upsert_by_phone(user_service, mock_db, mock_context):
    """Existing user updated when matched by phone number."""
    mock_db.add_user(id=1, phone_number="+1234567890")

    request = users_pb2.CreateUserRequest(
        phone_number="+1234567890",
        email="new@example.com",
    )

    response = await user_service.CreateUser(request, mock_context)

    assert response.user_id == "1"
    assert mock_db.users[1]["email"] == "new@example.com"
    assert mock_context.code is None


@pytest.mark.asyncio
async def test_create_user_no_identifier(user_service, mock_context):
    """INVALID_ARGUMENT when no identifier provided."""
    request = users_pb2.CreateUserRequest()

    with pytest.raises(GrpcAbortException):
        await user_service.CreateUser(request, mock_context)

    assert mock_context.code == grpc.StatusCode.INVALID_ARGUMENT


@pytest.mark.asyncio
async def test_create_user_db_error(user_service, mock_db, mock_context):
    """INTERNAL error when database raises exception."""
    mock_db.should_raise = Exception("Connection refused")

    request = users_pb2.CreateUserRequest(email="test@example.com")

    with pytest.raises(GrpcAbortException):
        await user_service.CreateUser(request, mock_context)

    assert mock_context.code == grpc.StatusCode.INTERNAL


# ============ Identity Collision Tests ============


@pytest.mark.asyncio
async def test_identity_collision_email_and_phone_different_users(user_service, mock_db, mock_context):
    """INVALID_ARGUMENT with IDENTITY_CONFLICT when email and phone match different users."""
    mock_db.add_user(id=1, email="user1@example.com")
    mock_db.add_user(id=2, phone_number="+1234567890")

    request = users_pb2.CreateUserRequest(
        email="user1@example.com",
        phone_number="+1234567890",
    )

    with pytest.raises(GrpcAbortException):
        await user_service.CreateUser(request, mock_context)

    assert mock_context.code == grpc.StatusCode.INVALID_ARGUMENT


@pytest.mark.asyncio
async def test_identity_collision_google_and_apple_different_users(user_service, mock_db, mock_context):
    """INVALID_ARGUMENT with IDENTITY_CONFLICT when google_id and apple_id match different users."""
    mock_db.add_user(id=1, google_id="google_123")
    mock_db.add_user(id=2, apple_id="apple_456")

    request = users_pb2.CreateUserRequest(
        google_id="google_123",
        apple_id="apple_456",
    )

    with pytest.raises(GrpcAbortException):
        await user_service.CreateUser(request, mock_context)

    assert mock_context.code == grpc.StatusCode.INVALID_ARGUMENT


@pytest.mark.asyncio
async def test_identity_collision_three_different_users(user_service, mock_db, mock_context):
    """INVALID_ARGUMENT when identifiers match three different users."""
    mock_db.add_user(id=1, email="user1@example.com")
    mock_db.add_user(id=2, phone_number="+1234567890")
    mock_db.add_user(id=3, google_id="google_123")

    request = users_pb2.CreateUserRequest(
        email="user1@example.com",
        phone_number="+1234567890",
        google_id="google_123",
    )

    with pytest.raises(GrpcAbortException):
        await user_service.CreateUser(request, mock_context)

    assert mock_context.code == grpc.StatusCode.INVALID_ARGUMENT


@pytest.mark.asyncio
async def test_no_collision_same_user_multiple_identifiers(user_service, mock_db, mock_context):
    """No collision when multiple identifiers match the SAME user."""
    mock_db.add_user(id=1, email="user@example.com", google_id="google_123")

    request = users_pb2.CreateUserRequest(
        email="user@example.com",
        google_id="google_123",
        username="newname",
    )

    response = await user_service.CreateUser(request, mock_context)

    assert response.user_id == "1"
    assert mock_db.users[1]["username"] == "newname"
    assert mock_context.code is None


@pytest.mark.asyncio
async def test_no_collision_one_identifier_new_user(user_service, mock_db, mock_context):
    """No collision when only one identifier provided for existing user."""
    mock_db.add_user(id=1, email="existing@example.com")

    # Different email, creates new user
    request = users_pb2.CreateUserRequest(
        email="new@example.com",
    )

    response = await user_service.CreateUser(request, mock_context)

    assert response.user_id == "2"
    assert mock_context.code is None
