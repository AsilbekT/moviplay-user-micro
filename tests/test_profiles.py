"""Tests for Profile RPCs."""
import pytest
import grpc

from proto import users_pb2
from utils.grpc_errors import GrpcAbortException


# ============ CreateProfile Tests ============


@pytest.mark.asyncio
async def test_create_profile_success(user_service, mock_db, mock_context):
    """Create profile successfully."""
    mock_db.add_user(id=1, email="test@example.com")

    request = users_pb2.CreateProfileRequest(
        user_id=1,
        name="Main Profile",
        is_kids=False,
        avatar="avatar1",
        language="en",
        maturity_level="all",
    )

    response = await user_service.CreateProfile(request, mock_context)

    assert response.profile.id == 1
    assert response.profile.user_id == 1
    assert response.profile.name == "Main Profile"
    assert response.profile.is_kids is False
    assert response.profile.avatar == "avatar1"
    assert response.profile.language == "en"
    assert mock_context.code is None


@pytest.mark.asyncio
async def test_create_profile_with_defaults(user_service, mock_db, mock_context):
    """Create profile with default values."""
    mock_db.add_user(id=1)

    request = users_pb2.CreateProfileRequest(
        user_id=1,
        name="Default Profile",
    )

    response = await user_service.CreateProfile(request, mock_context)

    assert response.profile.name == "Default Profile"
    assert response.profile.is_kids is False
    assert response.profile.language == "uz"
    assert response.profile.maturity_level == "all"
    assert mock_context.code is None


@pytest.mark.asyncio
async def test_create_profile_kids(user_service, mock_db, mock_context):
    """Create kids profile."""
    mock_db.add_user(id=1)

    request = users_pb2.CreateProfileRequest(
        user_id=1,
        name="Kids Profile",
        is_kids=True,
    )

    response = await user_service.CreateProfile(request, mock_context)

    assert response.profile.is_kids is True
    assert mock_context.code is None


@pytest.mark.asyncio
async def test_create_profile_invalid_user_id(user_service, mock_context):
    """INVALID_ARGUMENT when user_id is invalid."""
    request = users_pb2.CreateProfileRequest(user_id=0, name="Test")

    with pytest.raises(GrpcAbortException):
        await user_service.CreateProfile(request, mock_context)

    assert mock_context.code == grpc.StatusCode.INVALID_ARGUMENT


@pytest.mark.asyncio
async def test_create_profile_negative_user_id(user_service, mock_context):
    """INVALID_ARGUMENT when user_id is negative."""
    request = users_pb2.CreateProfileRequest(user_id=-1, name="Test")

    with pytest.raises(GrpcAbortException):
        await user_service.CreateProfile(request, mock_context)

    assert mock_context.code == grpc.StatusCode.INVALID_ARGUMENT


@pytest.mark.asyncio
async def test_create_profile_empty_name(user_service, mock_db, mock_context):
    """INVALID_ARGUMENT when name is empty."""
    mock_db.add_user(id=1)

    request = users_pb2.CreateProfileRequest(user_id=1, name="")

    with pytest.raises(GrpcAbortException):
        await user_service.CreateProfile(request, mock_context)

    assert mock_context.code == grpc.StatusCode.INVALID_ARGUMENT


@pytest.mark.asyncio
async def test_create_profile_whitespace_name(user_service, mock_db, mock_context):
    """INVALID_ARGUMENT when name is only whitespace."""
    mock_db.add_user(id=1)

    request = users_pb2.CreateProfileRequest(user_id=1, name="   ")

    with pytest.raises(GrpcAbortException):
        await user_service.CreateProfile(request, mock_context)

    assert mock_context.code == grpc.StatusCode.INVALID_ARGUMENT


@pytest.mark.asyncio
async def test_create_profile_name_too_long(user_service, mock_db, mock_context):
    """INVALID_ARGUMENT when name exceeds 50 characters."""
    mock_db.add_user(id=1)

    request = users_pb2.CreateProfileRequest(user_id=1, name="x" * 51)

    with pytest.raises(GrpcAbortException):
        await user_service.CreateProfile(request, mock_context)

    assert mock_context.code == grpc.StatusCode.INVALID_ARGUMENT


@pytest.mark.asyncio
async def test_create_profile_name_max_length(user_service, mock_db, mock_context):
    """Profile created with 50 character name (max length)."""
    mock_db.add_user(id=1)

    request = users_pb2.CreateProfileRequest(user_id=1, name="x" * 50)

    response = await user_service.CreateProfile(request, mock_context)

    assert len(response.profile.name) == 50
    assert mock_context.code is None


@pytest.mark.asyncio
async def test_create_profile_duplicate_name(user_service, mock_db, mock_context):
    """ALREADY_EXISTS when profile name already exists for user."""
    mock_db.add_user(id=1)
    mock_db.add_profile(id=1, user_id=1, name="Existing")

    request = users_pb2.CreateProfileRequest(user_id=1, name="Existing")

    with pytest.raises(GrpcAbortException):
        await user_service.CreateProfile(request, mock_context)

    assert mock_context.code == grpc.StatusCode.ALREADY_EXISTS


@pytest.mark.asyncio
async def test_create_profile_same_name_different_user(user_service, mock_db, mock_context):
    """Profile created with same name for different user."""
    mock_db.add_user(id=1)
    mock_db.add_user(id=2)
    mock_db.add_profile(id=1, user_id=1, name="SharedName")

    request = users_pb2.CreateProfileRequest(user_id=2, name="SharedName")

    response = await user_service.CreateProfile(request, mock_context)

    assert response.profile.name == "SharedName"
    assert response.profile.user_id == 2
    assert mock_context.code is None


@pytest.mark.asyncio
async def test_create_profile_limit_reached(user_service, mock_db, mock_context):
    """FAILED_PRECONDITION when user has 5 profiles."""
    mock_db.add_user(id=1)
    for i in range(5):
        mock_db.add_profile(user_id=1, name=f"Profile{i}")

    request = users_pb2.CreateProfileRequest(user_id=1, name="SixthProfile")

    with pytest.raises(GrpcAbortException):
        await user_service.CreateProfile(request, mock_context)

    assert mock_context.code == grpc.StatusCode.FAILED_PRECONDITION


@pytest.mark.asyncio
async def test_create_profile_at_limit(user_service, mock_db, mock_context):
    """Profile created when user has 4 profiles (under limit)."""
    mock_db.add_user(id=1)
    for i in range(4):
        mock_db.add_profile(user_id=1, name=f"Profile{i}")

    request = users_pb2.CreateProfileRequest(user_id=1, name="FifthProfile")

    response = await user_service.CreateProfile(request, mock_context)

    assert response.profile.name == "FifthProfile"
    assert mock_context.code is None


# ============ ListProfiles Tests ============


@pytest.mark.asyncio
async def test_list_profiles_success(user_service, mock_db, mock_context):
    """List all profiles for a user."""
    mock_db.add_user(id=1)
    mock_db.add_profile(id=1, user_id=1, name="Profile1")
    mock_db.add_profile(id=2, user_id=1, name="Profile2")

    request = users_pb2.ListProfilesRequest(user_id=1)

    response = await user_service.ListProfiles(request, mock_context)

    assert len(response.profiles) == 2
    names = [p.name for p in response.profiles]
    assert "Profile1" in names
    assert "Profile2" in names
    assert mock_context.code is None


@pytest.mark.asyncio
async def test_list_profiles_empty(user_service, mock_db, mock_context):
    """Empty list returned when user has no profiles."""
    mock_db.add_user(id=1)

    request = users_pb2.ListProfilesRequest(user_id=1)

    response = await user_service.ListProfiles(request, mock_context)

    assert len(response.profiles) == 0
    assert mock_context.code is None


@pytest.mark.asyncio
async def test_list_profiles_only_user_profiles(user_service, mock_db, mock_context):
    """Only returns profiles belonging to the specified user."""
    mock_db.add_user(id=1)
    mock_db.add_user(id=2)
    mock_db.add_profile(id=1, user_id=1, name="User1Profile")
    mock_db.add_profile(id=2, user_id=2, name="User2Profile")

    request = users_pb2.ListProfilesRequest(user_id=1)

    response = await user_service.ListProfiles(request, mock_context)

    assert len(response.profiles) == 1
    assert response.profiles[0].name == "User1Profile"
    assert mock_context.code is None


@pytest.mark.asyncio
async def test_list_profiles_invalid_user_id(user_service, mock_context):
    """INVALID_ARGUMENT when user_id is invalid."""
    request = users_pb2.ListProfilesRequest(user_id=0)

    with pytest.raises(GrpcAbortException):
        await user_service.ListProfiles(request, mock_context)

    assert mock_context.code == grpc.StatusCode.INVALID_ARGUMENT


# ============ GetProfile Tests ============


@pytest.mark.asyncio
async def test_get_profile_found(user_service, mock_db, mock_context):
    """Get profile by ID."""
    mock_db.add_user(id=1)
    mock_db.add_profile(id=1, user_id=1, name="TestProfile", is_kids=True)

    request = users_pb2.GetProfileRequest(profile_id=1)

    response = await user_service.GetProfile(request, mock_context)

    assert response.profile.id == 1
    assert response.profile.user_id == 1
    assert response.profile.name == "TestProfile"
    assert response.profile.is_kids is True
    assert mock_context.code is None


@pytest.mark.asyncio
async def test_get_profile_not_found(user_service, mock_context):
    """NOT_FOUND when profile does not exist."""
    request = users_pb2.GetProfileRequest(profile_id=999)

    with pytest.raises(GrpcAbortException):
        await user_service.GetProfile(request, mock_context)

    assert mock_context.code == grpc.StatusCode.NOT_FOUND


@pytest.mark.asyncio
async def test_get_profile_invalid_id(user_service, mock_context):
    """INVALID_ARGUMENT when profile_id is invalid."""
    request = users_pb2.GetProfileRequest(profile_id=0)

    with pytest.raises(GrpcAbortException):
        await user_service.GetProfile(request, mock_context)

    assert mock_context.code == grpc.StatusCode.INVALID_ARGUMENT


@pytest.mark.asyncio
async def test_get_profile_negative_id(user_service, mock_context):
    """INVALID_ARGUMENT when profile_id is negative."""
    request = users_pb2.GetProfileRequest(profile_id=-1)

    with pytest.raises(GrpcAbortException):
        await user_service.GetProfile(request, mock_context)

    assert mock_context.code == grpc.StatusCode.INVALID_ARGUMENT


# ============ UpdateProfile Tests ============


@pytest.mark.asyncio
async def test_update_profile_success(user_service, mock_db, mock_context):
    """Update profile fields."""
    mock_db.add_user(id=1)
    mock_db.add_profile(id=1, user_id=1, name="OldName", is_kids=False)

    request = users_pb2.UpdateProfileRequest(
        profile_id=1,
        name="NewName",
        is_kids=True,
        update_mask=["name", "is_kids"],
    )

    response = await user_service.UpdateProfile(request, mock_context)

    assert response.profile.name == "NewName"
    assert response.profile.is_kids is True
    assert mock_context.code is None


@pytest.mark.asyncio
async def test_update_profile_partial(user_service, mock_db, mock_context):
    """Update only specified fields via update_mask."""
    mock_db.add_user(id=1)
    mock_db.add_profile(id=1, user_id=1, name="Original", language="uz")

    request = users_pb2.UpdateProfileRequest(
        profile_id=1,
        language="en",
        update_mask=["language"],
    )

    response = await user_service.UpdateProfile(request, mock_context)

    assert response.profile.name == "Original"  # Unchanged
    assert response.profile.language == "en"    # Updated
    assert mock_context.code is None


@pytest.mark.asyncio
async def test_update_profile_not_found(user_service, mock_context):
    """NOT_FOUND when profile does not exist."""
    request = users_pb2.UpdateProfileRequest(profile_id=999, name="Test")

    with pytest.raises(GrpcAbortException):
        await user_service.UpdateProfile(request, mock_context)

    assert mock_context.code == grpc.StatusCode.NOT_FOUND


@pytest.mark.asyncio
async def test_update_profile_invalid_id(user_service, mock_context):
    """INVALID_ARGUMENT when profile_id is invalid."""
    request = users_pb2.UpdateProfileRequest(profile_id=0, name="Test")

    with pytest.raises(GrpcAbortException):
        await user_service.UpdateProfile(request, mock_context)

    assert mock_context.code == grpc.StatusCode.INVALID_ARGUMENT


@pytest.mark.asyncio
async def test_update_profile_duplicate_name(user_service, mock_db, mock_context):
    """ALREADY_EXISTS when updating to an existing name."""
    mock_db.add_user(id=1)
    mock_db.add_profile(id=1, user_id=1, name="Profile1")
    mock_db.add_profile(id=2, user_id=1, name="Profile2")

    request = users_pb2.UpdateProfileRequest(
        profile_id=2,
        name="Profile1",
        update_mask=["name"],
    )

    with pytest.raises(GrpcAbortException):
        await user_service.UpdateProfile(request, mock_context)

    assert mock_context.code == grpc.StatusCode.ALREADY_EXISTS


@pytest.mark.asyncio
async def test_update_profile_same_name_no_change(user_service, mock_db, mock_context):
    """Update allowed when name remains the same."""
    mock_db.add_user(id=1)
    mock_db.add_profile(id=1, user_id=1, name="SameName")

    request = users_pb2.UpdateProfileRequest(
        profile_id=1,
        name="SameName",
        is_kids=True,
        update_mask=["name", "is_kids"],
    )

    response = await user_service.UpdateProfile(request, mock_context)

    assert response.profile.name == "SameName"
    assert response.profile.is_kids is True
    assert mock_context.code is None


@pytest.mark.asyncio
async def test_update_profile_name_too_long(user_service, mock_db, mock_context):
    """INVALID_ARGUMENT when new name exceeds 50 characters."""
    mock_db.add_user(id=1)
    mock_db.add_profile(id=1, user_id=1, name="Original")

    request = users_pb2.UpdateProfileRequest(
        profile_id=1,
        name="x" * 51,
        update_mask=["name"],
    )

    with pytest.raises(GrpcAbortException):
        await user_service.UpdateProfile(request, mock_context)

    assert mock_context.code == grpc.StatusCode.INVALID_ARGUMENT


# ============ DeleteProfile Tests ============


@pytest.mark.asyncio
async def test_delete_profile_success(user_service, mock_db, mock_context):
    """Delete profile successfully."""
    mock_db.add_user(id=1)
    mock_db.add_profile(id=1, user_id=1, name="ToDelete")

    request = users_pb2.DeleteProfileRequest(profile_id=1)

    response = await user_service.DeleteProfile(request, mock_context)

    assert response.success is True
    assert 1 not in mock_db.profiles
    assert mock_context.code is None


@pytest.mark.asyncio
async def test_delete_profile_not_found(user_service, mock_context):
    """NOT_FOUND when profile does not exist."""
    request = users_pb2.DeleteProfileRequest(profile_id=999)

    with pytest.raises(GrpcAbortException):
        await user_service.DeleteProfile(request, mock_context)

    assert mock_context.code == grpc.StatusCode.NOT_FOUND


@pytest.mark.asyncio
async def test_delete_profile_invalid_id(user_service, mock_context):
    """INVALID_ARGUMENT when profile_id is invalid."""
    request = users_pb2.DeleteProfileRequest(profile_id=0)

    with pytest.raises(GrpcAbortException):
        await user_service.DeleteProfile(request, mock_context)

    assert mock_context.code == grpc.StatusCode.INVALID_ARGUMENT


@pytest.mark.asyncio
async def test_delete_profile_negative_id(user_service, mock_context):
    """INVALID_ARGUMENT when profile_id is negative."""
    request = users_pb2.DeleteProfileRequest(profile_id=-1)

    with pytest.raises(GrpcAbortException):
        await user_service.DeleteProfile(request, mock_context)

    assert mock_context.code == grpc.StatusCode.INVALID_ARGUMENT
