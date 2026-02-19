"""Centralized gRPC error handling with structured error responses."""
from __future__ import annotations

import grpc
from grpc_status import rpc_status
from google.rpc import status_pb2, error_details_pb2
from google.protobuf import any_pb2


class GrpcAbortException(BaseException):
    """Exception raised by abort() to exit the handler.

    Inherits from BaseException (not Exception) so that generic
    `except Exception:` handlers don't catch it.
    """
    pass


class FieldViolation:
    """Represents a single field validation error."""

    def __init__(self, field: str, description: str):
        self.field = field
        self.description = description


class ReasonCodes:
    """Stable machine-readable reason codes."""

    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    INVALID_ID = "INVALID_ID"
    INVALID_EMAIL = "INVALID_EMAIL"
    INVALID_PHONE = "INVALID_PHONE"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    PROFILE_NOT_FOUND = "PROFILE_NOT_FOUND"
    IDENTITY_CONFLICT = "IDENTITY_CONFLICT"
    DUPLICATE_IDENTIFIER = "DUPLICATE_IDENTIFIER"
    PROFILE_NAME_EXISTS = "PROFILE_NAME_EXISTS"
    PROFILE_LIMIT_REACHED = "PROFILE_LIMIT_REACHED"
    DB_UNAVAILABLE = "DB_UNAVAILABLE"
    DB_TIMEOUT = "DB_TIMEOUT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


async def abort(
    context: grpc.ServicerContext,
    grpc_code: grpc.StatusCode,
    reason: str,
    message: str,
    fields: list[FieldViolation] | None = None,
    domain: str = "users.moviplay",
) -> None:
    """
    Abort the RPC with a structured error response.

    Args:
        context: gRPC servicer context
        grpc_code: gRPC status code (e.g., INVALID_ARGUMENT, NOT_FOUND)
        reason: Machine-readable reason code (e.g., USER_NOT_FOUND, IDENTITY_CONFLICT)
        message: Human-readable error message
        fields: Optional list of field violations for validation errors
        domain: Error domain (default: users.moviplay)

    Raises:
        This function does not return - it aborts the RPC by calling
        context.abort_with_status() which raises an exception.
    """
    details = []

    # Add ErrorInfo with stable machine-readable reason
    error_info = error_details_pb2.ErrorInfo(reason=reason, domain=domain)
    error_info_any = any_pb2.Any()
    error_info_any.Pack(error_info)
    details.append(error_info_any)

    # Add BadRequest with field violations if provided
    if fields:
        bad_request = error_details_pb2.BadRequest()
        for f in fields:
            violation = bad_request.field_violations.add()
            violation.field = f.field
            violation.description = f.description
        bad_request_any = any_pb2.Any()
        bad_request_any.Pack(bad_request)
        details.append(bad_request_any)

    # Build status with details
    status = status_pb2.Status(
        code=grpc_code.value[0],
        message=message,
    )
    status.details.extend(details)

    # Set the status on the context and raise GrpcAbortException.
    # grpc.aio's abort_with_status() raises AbortError (an Exception subclass),
    # which would be caught by generic `except Exception:` handlers in servicers.
    # We catch it here and re-raise as GrpcAbortException (a BaseException subclass)
    # so it passes through those handlers cleanly.
    try:
        await context.abort_with_status(rpc_status.to_status(status))
    except Exception:
        raise GrpcAbortException(message)
    raise GrpcAbortException(message)
