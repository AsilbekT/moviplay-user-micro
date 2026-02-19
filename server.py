import grpc
import asyncio
import json
from services.user_service import UserService
from db.database import Database
from proto import users_pb2_grpc
from utils.config import settings


_db_ref = None


async def _handle_health(reader, writer):
    """Minimal HTTP health handler on a raw asyncio TCP server."""
    try:
        await reader.read(4096)  # consume request
        try:
            if _db_ref and _db_ref.pool:
                async with _db_ref.pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
            body = json.dumps({"status": "healthy", "service": "user-service"})
            status_line = "HTTP/1.1 200 OK"
        except Exception as e:
            body = json.dumps({"status": "unhealthy", "service": "user-service", "error": str(e)})
            status_line = "HTTP/1.1 503 Service Unavailable"

        response = f"{status_line}\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n{body}"
        writer.write(response.encode())
        await writer.drain()
    finally:
        writer.close()


async def serve():
    global _db_ref
    db = Database(settings.database_url)

    try:
        await db.connect()
    except Exception as e:
        print(f"Failed to connect to the database: {e}")
        return

    _db_ref = db

    server = grpc.aio.server()
    users_pb2_grpc.add_UserServiceServicer_to_server(UserService(db), server)
    server.add_insecure_port('[::]:50051')

    # HTTP health check server on port 50061
    health_server = await asyncio.start_server(_handle_health, "0.0.0.0", 50061)

    try:
        print("User service running on port 50051...")
        print("User service health check on port 50061...")
        await server.start()
        await server.wait_for_termination()
    except asyncio.CancelledError:
        await server.stop(None)
    finally:
        health_server.close()
        await health_server.wait_closed()
        await db.close()

if __name__ == '__main__':
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        pass
