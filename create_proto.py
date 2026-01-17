from grpc_tools import protoc

protoc.main((
    '',
    '--proto_path=proto',
    '--python_out=proto',  # Output directory for Python files
    '--grpc_python_out=proto',  # Output directory for gRPC files
    'proto/users.proto',  
))


# python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. proto/users.proto