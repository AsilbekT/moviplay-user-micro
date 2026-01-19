#!/usr/bin/env python3
"""
Generate Python protobuf code from shared/proto/users.proto (canonical source)

This script generates the Python gRPC code from the canonical users.proto.
Prefer using 'make proto' instead of running this script directly.
"""

import grpc_tools
from grpc_tools import protoc
import os

# Get the path to google protobuf includes (for google.protobuf.field_mask)
grpc_tools_path = os.path.dirname(grpc_tools.__file__)
google_proto_path = os.path.join(grpc_tools_path, '_proto')

# Use shared/proto as the canonical source
result = protoc.main((
    '',
    '--proto_path=../shared/proto',
    f'--proto_path={google_proto_path}',
    '--python_out=proto',
    '--grpc_python_out=proto',
    '../shared/proto/users.proto',
))

if result != 0:
    print(f"Protobuf generation failed with code {result}")
    exit(result)

# Fix import in generated grpc file to use package-relative import
grpc_file = os.path.join(os.path.dirname(__file__), 'proto', 'users_pb2_grpc.py')
with open(grpc_file, 'r') as f:
    content = f.read()

content = content.replace(
    'import users_pb2 as users__pb2',
    'from proto import users_pb2 as users__pb2'
)

with open(grpc_file, 'w') as f:
    f.write(content)

print("Protobuf code generated successfully in proto/")


# Alternative command line:
# python -m grpc_tools.protoc -I../shared/proto --python_out=proto --grpc_python_out=proto ../shared/proto/users.proto
