"""Tests for GetUser RPC."""
import pytest
import grpc

from proto import users_pb2
from utils.grpc_errors import GrpcAbortException


@pytest.mark.asyncio
async def test_get_user_found(user_service, mock_db, mock_context):
    """User found and returned."""
    mock_db.add_user(
        id=1,
        username="testuser",
        email="test@example.com",
        phone_number="+1234567890",
        google_id="google_123",
        apple_id="apple_123",
    )

    request = users_pb2.GetUserRequest(user_id="1")

    response = await user_service.GetUser(request, mock_context)

    assert response.user_id == "1"
    assert response.username == "testuser"
    assert response.email == "test@example.com"
    assert response.phone_number == "+1234567890"
    assert response.google_id == "google_123"
    assert response.apple_id == "apple_123"
    assert mock_context.code is None


@pytest.mark.asyncio
async def test_get_user_not_found(user_service, mock_context):
    """NOT_FOUND when user does not exist."""
    request = users_pb2.GetUserRequest(user_id="999")

    with pytest.raises(GrpcAbortException):
        await user_service.GetUser(request, mock_context)

    assert mock_context.code == grpc.StatusCode.NOT_FOUND


@pytest.mark.asyncio
async def test_get_user_invalid_id_empty(user_service, mock_context):
    """INVALID_ARGUMENT when user_id is empty."""
    request = users_pb2.GetUserRequest(user_id="")

    with pytest.raises(GrpcAbortException):
        await user_service.GetUser(request, mock_context)

    assert mock_context.code == grpc.StatusCode.INVALID_ARGUMENT


@pytest.mark.asyncio
async def test_get_user_invalid_id_non_numeric(user_service, mock_context):
    """INVALID_ARGUMENT when user_id is not numeric."""
    request = users_pb2.GetUserRequest(user_id="abc")

    with pytest.raises(GrpcAbortException):
        await user_service.GetUser(request, mock_context)

    assert mock_context.code == grpc.StatusCode.INVALID_ARGUMENT


@pytest.mark.asyncio
async def test_get_user_invalid_id_negative(user_service, mock_context):
    """INVALID_ARGUMENT when user_id contains non-digit characters."""
    request = users_pb2.GetUserRequest(user_id="-1")

    with pytest.raises(GrpcAbortException):
        await user_service.GetUser(request, mock_context)

    assert mock_context.code == grpc.StatusCode.INVALID_ARGUMENT


@pytest.mark.asyncio
async def test_get_user_with_empty_optional_fields(user_service, mock_db, mock_context):
    """User returned with empty strings for unset optional fields."""
    mock_db.add_user(id=1, email="test@example.com")

    request = users_pb2.GetUserRequest(user_id="1")

    response = await user_service.GetUser(request, mock_context)

    assert response.user_id == "1"
    assert response.email == "test@example.com"
    assert response.username == ""
    assert response.phone_number == ""
    assert response.google_id == ""
    assert response.apple_id == ""
    assert mock_context.code is None


@pytest.mark.asyncio
async def test_get_user_db_error(user_service, mock_db, mock_context):
    """INTERNAL error when database raises exception."""
    mock_db.should_raise = Exception("Connection refused")

    request = users_pb2.GetUserRequest(user_id="1")

    with pytest.raises(GrpcAbortException):
        await user_service.GetUser(request, mock_context)

    assert mock_context.code == grpc.StatusCode.INTERNAL
