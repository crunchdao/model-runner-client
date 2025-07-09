import json
import struct
import io
import pandas
import pyarrow.parquet as pq
import pyarrow as pa
from model_runner_client.grpc.generated.commons_pb2 import VariantType


# Encoder: Converts data to bytes
def encode_data(data_type: VariantType, data) -> bytes:
    if data_type == VariantType.NONE:
        return b""
    elif data_type == VariantType.DOUBLE:
        return struct.pack("d", data)
    elif data_type == VariantType.INT:
        return data.to_bytes(8, byteorder="little", signed=True)
    elif data_type == VariantType.STRING:
        return data.encode("utf-8")
    elif data_type == VariantType.PARQUET:
        table = pa.Table.from_pandas(data) if isinstance(data, pandas.DataFrame) else data
        sink = io.BytesIO()
        pq.write_table(table, sink)
        return sink.getvalue()
    elif data_type == VariantType.JSON:
        try:
            json_data = json.dumps(data)  # Convert the object to a JSON string
            return json_data.encode("utf-8")  # Return the JSON string as bytes
        except TypeError as e:
            raise ValueError(f"Data cannot be serialized to JSON: {e}")
    else:
        raise ValueError(f"Unsupported data type: {data_type}")


# Decoder: Converts bytes to data
def decode_data(data_bytes: bytes, data_type: VariantType):
    if data_type == VariantType.NONE:
        return None
    elif data_type == VariantType.DOUBLE:
        return struct.unpack("d", data_bytes)[0]
    elif data_type == VariantType.INT:
        return int.from_bytes(data_bytes, byteorder="little", signed=True)
    elif data_type == VariantType.STRING:
        return data_bytes.decode("utf-8")
    elif data_type == VariantType.PARQUET:
        buffer = io.BytesIO(data_bytes)
        return pq.read_table(buffer).to_pandas()
    elif data_type == VariantType.JSON:
        try:
            json_data = data_bytes.decode("utf-8")
            return json.loads(json_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to decode JSON data: {e}")

    else:
        raise ValueError(f"Unsupported data type: {data_type}")


def detect_data_type(data) -> VariantType:
    """
    Detects the data type based on the Python object and returns
    the corresponding VariantType enum.
    """
    if data is None:
        return VariantType.NONE
    elif isinstance(data, float):
        return VariantType.DOUBLE
    elif isinstance(data, int):
        return VariantType.INT
    elif isinstance(data, str):
        return VariantType.STRING
    elif isinstance(data, pandas.DataFrame):
        return VariantType.PARQUET
    elif isinstance(data, dict) or isinstance(data, list):
        return VariantType.JSON
    else:
        raise ValueError(f"Unsupported data type: {type(data)}")
