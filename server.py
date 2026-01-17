import grpc
import asyncio
from services.user_service import UserService
from db.database import Database
from proto import users_pb2_grpc
from utils.config import settings


async def serve():
    db = Database(settings.database_url)

    try:
        await db.connect()
    except Exception as e:
        print(f"Failed to connect to the database: {e}")
        return

    server = grpc.aio.server()
    users_pb2_grpc.add_UserServiceServicer_to_server(UserService(db), server)
    server.add_insecure_port('[::]:50051')

    try:
        print("User service running on port 50051...")
        await server.start()
        await server.wait_for_termination()
    except asyncio.CancelledError:
        await server.stop(None)
    finally:
        await db.close()

if __name__ == '__main__':
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        pass
