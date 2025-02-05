import json
import struct
import io
import pandas
import pyarrow.parquet as pq

from model_runner_client.protos.model_runner_pb2 import DataType


# Encoder: Converts data to bytes
def encode_data(data_type: DataType, data) -> bytes:
    if data_type == DataType.DOUBLE:
        return struct.pack("d", data)
    elif data_type == DataType.INT:
        return data.to_bytes(8, byteorder="little", signed=True)
    elif data_type == DataType.STRING:
        return data.encode("utf-8")
    elif data_type == DataType.PARQUET:
        table = pandas.Table.from_pandas(data)
        sink = io.BytesIO()
        pandas.write_table(table, sink)
        return sink.getvalue()
    elif data_type == DataType.JSON:
        try:
            json_data = json.dumps(data)  # Convert the object to a JSON string
            return json_data.encode("utf-8")  # Return the JSON string as bytes
        except TypeError as e:
            raise ValueError(f"Data cannot be serialized to JSON: {e}")
    else:
        raise ValueError(f"Unsupported data type: {data_type}")


# Decoder: Converts bytes to data
def decode_data(data_bytes: bytes, data_type: DataType):
    if data_type == DataType.DOUBLE:
        return struct.unpack("d", data_bytes)[0]
    elif data_type == DataType.INT:
        return int.from_bytes(data_bytes, byteorder="little", signed=True)
    elif data_type == DataType.STRING:
        return data_bytes.decode("utf-8")
    elif data_type == DataType.PARQUET:
        buffer = io.BytesIO(data_bytes)
        return pq.read_table(buffer).to_pandas()
    elif data_type == DataType.JSON:
        try:
            json_data = data_bytes.decode("utf-8")
            return json.loads(json_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to decode JSON data: {e}")

    else:
        raise ValueError(f"Unsupported data type: {data_type}")


def detect_data_type(data) -> DataType:
    """
    Detects the data type based on the Python object and returns
    the corresponding DataType enum.
    """
    if isinstance(data, float):
        return DataType.DOUBLE
    elif isinstance(data, int):
        return DataType.INT
    elif isinstance(data, str):
        return DataType.STRING
    elif isinstance(data, pandas.DataFrame):
        return DataType.PARQUET
    elif isinstance(data, dict) or isinstance(data, list):
        return DataType.JSON
    else:
        raise ValueError(f"Unsupported data type: {type(data)}")
