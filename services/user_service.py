from proto import users_pb2, users_pb2_grpc
import grpc


class UserService(users_pb2_grpc.UserServiceServicer):
    def __init__(self, db):
        self.db = db

    async def CreateUser(self, request, context):
        try:
            user_id = await self.db.create_or_update_user(
                username=request.username if request.username else None,
                email=request.email if request.email else None,
                phone_number=request.phone_number if request.phone_number else None,
                google_id=request.google_id if request.google_id else None,
                apple_id=request.apple_id if request.apple_id else None
            )
            return users_pb2.UserResponse(
                user_id=str(user_id),
                username=request.username,
                email=request.email,
                phone_number=request.phone_number,
                google_id=request.google_id,
                apple_id=request.apple_id
            )
        except Exception as e:
            context.set_details(f"Internal server error: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            return users_pb2.UserResponse()

    async def GetUser(self, request, context):
        try:
            if not request.user_id or not request.user_id.isdigit():
                context.set_details("Invalid user_id format. Must be a non-empty numeric value.")
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                return users_pb2.UserResponse()

            user_id = int(request.user_id)
            user = await self.db.get_user(user_id)
            if not user:
                context.set_details("User not found.")
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return users_pb2.UserResponse()

            return users_pb2.UserResponse(
                user_id=str(user["id"]),
                username=user["username"] if user["username"] else "",
                email=user["email"] if user["email"] else "",
                phone_number=user["phone_number"] if user["phone_number"] else "",
                google_id=user["google_id"] if user["google_id"] else "",
                apple_id=user["apple_id"] if user["apple_id"] else ""
            )
        except Exception:
            context.set_details("An internal error occurred while processing the request.")
            context.set_code(grpc.StatusCode.INTERNAL)
            return users_pb2.UserResponse()