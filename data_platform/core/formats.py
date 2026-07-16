"""
Format Handler

Handles different data formats: Parquet, Arrow, CSV, SQL, Object Storage.
"""

import io
import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)


class FormatHandler(ABC):
    """Abstract base class for format handlers"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Format name"""
        pass
    
    @property
    @abstractmethod
    def extensions(self) -> List[str]:
        """File extensions for this format"""
        pass
    
    @abstractmethod
    def read(self, source: Any, **kwargs) -> Any:
        """Read data from source"""
        pass
    
    @abstractmethod
    def write(self, data: Any, destination: Any, **kwargs) -> Dict[str, Any]:
        """Write data to destination"""
        pass
    
    @abstractmethod
    def get_metadata(self, source: Any) -> Dict[str, Any]:
        """Get metadata from source"""
        pass


class ParquetHandler(FormatHandler):
    """Handler for Parquet format"""
    
    @property
    def name(self) -> str:
        return "parquet"
    
    @property
    def extensions(self) -> List[str]:
        return [".parquet", ".pq"]
    
    def read(self, source: Any, **kwargs) -> Any:
        """Read Parquet data"""
        import pandas as pd
        
        if isinstance(source, (str, os.PathLike)):
            return pd.read_parquet(source, **kwargs)
        elif isinstance(source, bytes):
            return pd.read_parquet(io.BytesIO(source), **kwargs)
        elif hasattr(source, "read"):
            return pd.read_parquet(source, **kwargs)
        else:
            raise ValueError(f"Unsupported source type: {type(source)}")
    
    def write(self, data: Any, destination: Any, **kwargs) -> Dict[str, Any]:
        """Write Parquet data"""
        import pandas as pd
        
        df = self._to_dataframe(data)
        size = 0
        
        if isinstance(destination, (str, os.PathLike)):
            df.to_parquet(destination, **kwargs)
            size = os.path.getsize(destination)
        elif isinstance(destination, bytes):
            buffer = io.BytesIO()
            df.to_parquet(buffer, **kwargs)
            destination.write(buffer.getvalue())
            size = buffer.tell()
        elif isinstance(destination, io.BytesIO):
            df.to_parquet(destination, **kwargs)
            size = destination.tell()
        elif hasattr(destination, "write"):
            # Duck typing for file-like objects
            buffer = io.BytesIO()
            df.to_parquet(buffer, **kwargs)
            destination.write(buffer.getvalue())
            size = buffer.tell()
        else:
            raise ValueError(f"Unsupported destination type: {type(destination)}")
        
        return {
            "format": self.name,
            "rows": len(df),
            "columns": len(df.columns),
            "size_bytes": size,
            "column_types": {col: str(dtype) for col, dtype in df.dtypes.items()},
        }
    
    def get_metadata(self, source: Any) -> Dict[str, Any]:
        """Get Parquet metadata"""
        import pandas as pd
        
        if isinstance(source, (str, os.PathLike)):
            pf = pd.read_parquet(source, columns=[])
            metadata = pf.schema.pandas_metadata if hasattr(pf, 'schema') else {}
            
            # Get basic stats from file
            stats = {
                "exists": os.path.exists(source),
                "size_bytes": os.path.getsize(source) if os.path.exists(source) else 0,
            }
            
            # Try to read column names
            try:
                df = pd.read_parquet(source)
                stats["rows"] = len(df)
                stats["columns"] = len(df.columns)
                stats["column_names"] = df.columns.tolist()
            except Exception:
                pass
            
            return stats
        else:
            return {"error": "Source must be a file path"}
    
    def _to_dataframe(self, data: Any) -> Any:
        """Convert to DataFrame"""
        import pandas as pd
        if isinstance(data, pd.DataFrame):
            return data
        elif isinstance(data, (list, dict)):
            return pd.DataFrame(data)
        return data


class ArrowHandler(FormatHandler):
    """Handler for Arrow format"""
    
    @property
    def name(self) -> str:
        return "arrow"
    
    @property
    def extensions(self) -> List[str]:
        return [".arrow", ".feather"]
    
    def read(self, source: Any, **kwargs) -> Any:
        """Read Arrow data"""
        import pandas as pd
        
        if isinstance(source, (str, os.PathLike)):
            return pd.read_feather(source, **kwargs)
        elif isinstance(source, bytes):
            return pd.read_feather(io.BytesIO(source), **kwargs)
        else:
            raise ValueError(f"Unsupported source type: {type(source)}")
    
    def write(self, data: Any, destination: Any, **kwargs) -> Dict[str, Any]:
        """Write Arrow data"""
        import pandas as pd
        
        df = self._to_dataframe(data)
        size = 0
        
        if isinstance(destination, (str, os.PathLike)):
            df.to_feather(destination, **kwargs)
            size = os.path.getsize(destination)
        elif isinstance(destination, bytes):
            buffer = io.BytesIO()
            df.to_feather(buffer, **kwargs)
            destination.write(buffer.getvalue())
            size = buffer.tell()
        elif isinstance(destination, io.BytesIO):
            df.to_feather(destination, **kwargs)
            size = destination.tell()
        elif hasattr(destination, "write"):
            buffer = io.BytesIO()
            df.to_feather(buffer, **kwargs)
            destination.write(buffer.getvalue())
            size = buffer.tell()
        else:
            raise ValueError(f"Unsupported destination type: {type(destination)}")
        
        return {
            "format": self.name,
            "rows": len(df),
            "columns": len(df.columns),
            "size_bytes": size,
        }
    
    def get_metadata(self, source: Any) -> Dict[str, Any]:
        """Get Arrow metadata"""
        return self._get_basic_metadata(source)
    
    def _to_dataframe(self, data: Any) -> Any:
        """Convert to DataFrame"""
        import pandas as pd
        if isinstance(data, pd.DataFrame):
            return data
        elif isinstance(data, (list, dict)):
            return pd.DataFrame(data)
        return data
    
    def _get_basic_metadata(self, source: Any) -> Dict[str, Any]:
        """Get basic file metadata"""
        if isinstance(source, (str, os.PathLike)):
            return {
                "exists": os.path.exists(source),
                "size_bytes": os.path.getsize(source) if os.path.exists(source) else 0,
            }
        return {}


class CSVHandler(FormatHandler):
    """Handler for CSV format"""
    
    @property
    def name(self) -> str:
        return "csv"
    
    @property
    def extensions(self) -> List[str]:
        return [".csv"]
    
    def read(self, source: Any, **kwargs) -> Any:
        """Read CSV data"""
        import pandas as pd
        
        if isinstance(source, (str, os.PathLike)):
            return pd.read_csv(source, **kwargs)
        elif isinstance(source, bytes):
            return pd.read_csv(io.BytesIO(source), **kwargs)
        elif hasattr(source, "read"):
            return pd.read_csv(source, **kwargs)
        else:
            raise ValueError(f"Unsupported source type: {type(source)}")
    
    def write(self, data: Any, destination: Any, **kwargs) -> Dict[str, Any]:
        """Write CSV data"""
        import pandas as pd
        
        df = self._to_dataframe(data)
        size = 0
        content = ""
        
        if isinstance(destination, (str, os.PathLike)):
            df.to_csv(destination, index=False, **kwargs)
            size = os.path.getsize(destination)
        elif isinstance(destination, bytes):
            buffer = io.StringIO()
            df.to_csv(buffer, index=False, **kwargs)
            content = buffer.getvalue()
            destination.write(content.encode())
            size = len(content)
        elif isinstance(destination, io.BytesIO):
            buffer = io.StringIO()
            df.to_csv(buffer, index=False, **kwargs)
            content = buffer.getvalue()
            destination.write(content.encode())
            size = len(content)
        elif isinstance(destination, io.StringIO):
            df.to_csv(destination, index=False, **kwargs)
            size = destination.tell()
        elif hasattr(destination, "write"):
            buffer = io.StringIO()
            df.to_csv(buffer, index=False, **kwargs)
            content = buffer.getvalue()
            # Check if it's a binary or text stream
            try:
                destination.write(content)
                size = len(content)
            except TypeError:
                destination.write(content.encode())
                size = len(content)
        else:
            raise ValueError(f"Unsupported destination type: {type(destination)}")
        
        return {
            "format": self.name,
            "rows": len(df),
            "columns": len(df.columns),
            "size_bytes": size,
        }
    
    def get_metadata(self, source: Any) -> Dict[str, Any]:
        """Get CSV metadata"""
        import pandas as pd
        
        if isinstance(source, (str, os.PathLike)):
            stats = {
                "exists": os.path.exists(source),
                "size_bytes": os.path.getsize(source) if os.path.exists(source) else 0,
            }
            
            try:
                # Count rows and get columns without loading all data
                df = pd.read_csv(source, nrows=0)
                stats["columns"] = len(df.columns)
                stats["column_names"] = df.columns.tolist()
                
                # Count lines
                with open(source, "r") as f:
                    stats["rows"] = sum(1 for _ in f) - 1  # Subtract header
            except Exception as e:
                stats["error"] = str(e)
            
            return stats
        return {}
    
    def _to_dataframe(self, data: Any) -> Any:
        """Convert to DataFrame"""
        import pandas as pd
        if isinstance(data, pd.DataFrame):
            return data
        elif isinstance(data, (list, dict)):
            return pd.DataFrame(data)
        return data


class JSONHandler(FormatHandler):
    """Handler for JSON format"""
    
    @property
    def name(self) -> str:
        return "json"
    
    @property
    def extensions(self) -> List[str]:
        return [".json"]
    
    def read(self, source: Any, **kwargs) -> Any:
        """Read JSON data"""
        import pandas as pd
        
        kwargs.setdefault("orient", "records")
        
        if isinstance(source, (str, os.PathLike)):
            return pd.read_json(source, **kwargs)
        elif isinstance(source, bytes):
            return pd.read_json(io.BytesIO(source), **kwargs)
        elif hasattr(source, "read"):
            return pd.read_json(source, **kwargs)
        else:
            raise ValueError(f"Unsupported source type: {type(source)}")
    
    def write(self, data: Any, destination: Any, **kwargs) -> Dict[str, Any]:
        """Write JSON data"""
        import pandas as pd
        
        df = self._to_dataframe(data)
        
        kwargs.setdefault("orient", "records")
        kwargs.setdefault("indent", 2)
        size = 0
        
        if isinstance(destination, (str, os.PathLike)):
            df.to_json(destination, **kwargs)
            size = os.path.getsize(destination)
        elif isinstance(destination, bytes):
            buffer = io.StringIO()
            df.to_json(buffer, **kwargs)
            destination.write(buffer.getvalue().encode())
            size = len(buffer.getvalue())
        elif isinstance(destination, io.StringIO):
            df.to_json(destination, **kwargs)
            size = destination.tell()
        elif hasattr(destination, "write"):
            buffer = io.StringIO()
            df.to_json(buffer, **kwargs)
            destination.write(buffer.getvalue())
            size = len(buffer.getvalue())
        else:
            raise ValueError(f"Unsupported destination type: {type(destination)}")
        
        return {
            "format": self.name,
            "rows": len(df),
            "columns": len(df.columns),
            "size_bytes": size,
        }
    
    def get_metadata(self, source: Any) -> Dict[str, Any]:
        """Get JSON metadata"""
        if isinstance(source, (str, os.PathLike)):
            return {
                "exists": os.path.exists(source),
                "size_bytes": os.path.getsize(source) if os.path.exists(source) else 0,
            }
        return {}
    
    def _to_dataframe(self, data: Any) -> Any:
        """Convert to DataFrame"""
        import pandas as pd
        if isinstance(data, pd.DataFrame):
            return data
        elif isinstance(data, (list, dict)):
            return pd.DataFrame(data)
        return data


class ObjectStorageHandler:
    """
    Handler for Object Storage (S3, GCS, Azure Blob, etc.)
    
    Supports multiple cloud providers with a unified interface.
    """
    
    def __init__(self, provider: str = "local"):
        self.provider = provider
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize object storage client"""
        if self.provider == "s3":
            self._init_s3()
        elif self.provider == "gcs":
            self._init_gcs()
        elif self.provider == "azure":
            self._init_azure()
        else:
            # Local filesystem
            pass
    
    def _init_s3(self) -> None:
        """Initialize S3 client"""
        try:
            import boto3
            self._client = boto3.client("s3")
            logger.info("S3 client initialized")
        except ImportError:
            logger.warning("boto3 not available, using local storage")
            self.provider = "local"
    
    def _init_gcs(self) -> None:
        """Initialize GCS client"""
        try:
            from google.cloud import storage
            self._client = storage.Client()
            logger.info("GCS client initialized")
        except ImportError:
            logger.warning("google-cloud-storage not available")
            self.provider = "local"
    
    def _init_azure(self) -> None:
        """Initialize Azure Blob client"""
        try:
            from azure.storage.blob import BlobServiceClient
            connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
            if connection_string:
                self._client = BlobServiceClient.from_connection_string(connection_string)
                logger.info("Azure Blob client initialized")
        except ImportError:
            logger.warning("azure-storage-blob not available")
            self.provider = "local"
    
    def upload(
        self,
        data: Any,
        bucket: str,
        key: str,
        format: str = "parquet",
        **kwargs,
    ) -> Dict[str, Any]:
        """Upload data to object storage"""
        import pandas as pd
        
        df = pd.DataFrame() if isinstance(data, pd.DataFrame) else data
        
        if self.provider == "s3":
            return self._upload_s3(df, bucket, key, format, **kwargs)
        elif self.provider == "gcs":
            return self._upload_gcs(df, bucket, key, format, **kwargs)
        elif self.provider == "azure":
            return self._upload_azure(df, bucket, key, format, **kwargs)
        else:
            return self._upload_local(df, bucket, key, format, **kwargs)
    
    def download(
        self,
        bucket: str,
        key: str,
        format: str = "parquet",
        **kwargs,
    ) -> Any:
        """Download data from object storage"""
        if self.provider == "s3":
            return self._download_s3(bucket, key, format, **kwargs)
        elif self.provider == "gcs":
            return self._download_gcs(bucket, key, format, **kwargs)
        elif self.provider == "azure":
            return self._download_azure(bucket, key, format, **kwargs)
        else:
            return self._download_local(bucket, key, format, **kwargs)
    
    def _upload_s3(self, data: Any, bucket: str, key: str, format: str, **kwargs) -> Dict[str, Any]:
        """Upload to S3"""
        buffer = io.BytesIO()
        self._write_to_buffer(data, format, buffer)
        buffer.seek(0)
        
        self._client.upload_fileobj(buffer, bucket, key, **kwargs)
        
        return {
            "provider": "s3",
            "bucket": bucket,
            "key": key,
            "size_bytes": buffer.tell(),
        }
    
    def _download_s3(self, bucket: str, key: str, format: str, **kwargs) -> Any:
        """Download from S3"""
        buffer = io.BytesIO()
        self._client.download_fileobj(bucket, key, buffer, **kwargs)
        buffer.seek(0)
        
        return self._read_from_buffer(buffer, format)
    
    def _upload_gcs(self, data: Any, bucket: str, key: str, format: str, **kwargs) -> Dict[str, Any]:
        """Upload to GCS"""
        buffer = io.BytesIO()
        self._write_to_buffer(data, format, buffer)
        buffer.seek(0)
        
        bucket_obj = self._client.bucket(bucket)
        blob = bucket_obj.blob(key)
        blob.upload_from_file(buffer, **kwargs)
        
        return {
            "provider": "gcs",
            "bucket": bucket,
            "key": key,
            "size_bytes": buffer.tell(),
        }
    
    def _download_gcs(self, bucket: str, key: str, format: str, **kwargs) -> Any:
        """Download from GCS"""
        bucket_obj = self._client.bucket(bucket)
        blob = bucket_obj.blob(key)
        buffer = io.BytesIO()
        blob.download_to_file(buffer, **kwargs)
        buffer.seek(0)
        
        return self._read_from_buffer(buffer, format)
    
    def _upload_azure(self, data: Any, bucket: str, key: str, format: str, **kwargs) -> Dict[str, Any]:
        """Upload to Azure Blob"""
        buffer = io.BytesIO()
        self._write_to_buffer(data, format, buffer)
        buffer.seek(0)
        
        container_client = self._client.get_container_client(bucket)
        blob_client = container_client.get_blob_client(key)
        blob_client.upload_blob(buffer, **kwargs)
        
        return {
            "provider": "azure",
            "container": bucket,
            "blob": key,
            "size_bytes": buffer.tell(),
        }
    
    def _download_azure(self, bucket: str, key: str, format: str, **kwargs) -> Any:
        """Download from Azure Blob"""
        container_client = self._client.get_container_client(bucket)
        blob_client = container_client.get_blob_client(key)
        buffer = io.BytesIO()
        blob_client.download_blob().readinto(buffer)
        buffer.seek(0)
        
        return self._read_from_buffer(buffer, format)
    
    def _upload_local(self, data: Any, path: str, key: str, format: str, **kwargs) -> Dict[str, Any]:
        """Upload to local filesystem"""
        full_path = os.path.join(path, key)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        self._write_to_file(data, format, full_path, **kwargs)
        
        return {
            "provider": "local",
            "path": full_path,
            "size_bytes": os.path.getsize(full_path),
        }
    
    def _download_local(self, path: str, key: str, format: str, **kwargs) -> Any:
        """Download from local filesystem"""
        full_path = os.path.join(path, key)
        return self._read_from_file(format, full_path, **kwargs)
    
    def _write_to_buffer(self, data: Any, format: str, buffer: io.BytesIO) -> None:
        """Write data to buffer in specified format"""
        if format == "parquet":
            data.to_parquet(buffer)
        elif format == "arrow":
            data.to_feather(buffer)
        elif format == "csv":
            data.to_csv(buffer, index=False)
            buffer.seek(0)
            buffer.write(buffer.read().encode())
        elif format == "json":
            data.to_json(buffer, orient="records")
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _read_from_buffer(self, buffer: io.BytesIO, format: str) -> Any:
        """Read data from buffer in specified format"""
        import pandas as pd
        
        if format == "parquet":
            return pd.read_parquet(buffer)
        elif format == "arrow":
            return pd.read_feather(buffer)
        elif format == "csv":
            return pd.read_csv(buffer)
        elif format == "json":
            return pd.read_json(buffer)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _write_to_file(self, data: Any, format: str, path: str, **kwargs) -> None:
        """Write data to file in specified format"""
        if format == "parquet":
            data.to_parquet(path, **kwargs)
        elif format == "arrow":
            data.to_feather(path, **kwargs)
        elif format == "csv":
            data.to_csv(path, index=False, **kwargs)
        elif format == "json":
            data.to_json(path, orient="records", **kwargs)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _read_from_file(self, format: str, path: str, **kwargs) -> Any:
        """Read data from file in specified format"""
        import pandas as pd
        
        if format == "parquet":
            return pd.read_parquet(path, **kwargs)
        elif format == "arrow":
            return pd.read_feather(path, **kwargs)
        elif format == "csv":
            return pd.read_csv(path, **kwargs)
        elif format == "json":
            return pd.read_json(path, **kwargs)
        else:
            raise ValueError(f"Unsupported format: {format}")


class FormatManager:
    """
    Unified format manager for all supported data formats.
    
    Supports:
    - Parquet
    - Arrow
    - CSV
    - JSON
    - SQL
    - Object Storage
    """
    
    def __init__(self):
        self._handlers: Dict[str, FormatHandler] = {
            "parquet": ParquetHandler(),
            "arrow": ArrowHandler(),
            "csv": CSVHandler(),
            "json": JSONHandler(),
        }
        
        self._object_storage = ObjectStorageHandler()
    
    def get_handler(self, format: str) -> Optional[FormatHandler]:
        """Get handler for format"""
        return self._handlers.get(format.lower())
    
    def detect_format(self, source: Any) -> Optional[str]:
        """Detect format from file extension"""
        if isinstance(source, (str, os.PathLike)):
            ext = os.path.splitext(str(source))[1].lower()
            for name, handler in self._handlers.items():
                if ext in handler.extensions:
                    return name
        return None
    
    def read(
        self,
        source: Any,
        format: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """Read data in any supported format"""
        if format is None:
            format = self.detect_format(source)
        
        if format is None:
            raise ValueError(f"Could not detect format for {source}")
        
        handler = self._handlers.get(format)
        if handler is None:
            raise ValueError(f"No handler for format: {format}")
        
        return handler.read(source, **kwargs)
    
    def write(
        self,
        data: Any,
        destination: Any,
        format: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Write data in any supported format"""
        handler = self._handlers.get(format)
        if handler is None:
            raise ValueError(f"No handler for format: {format}")
        
        return handler.write(data, destination, **kwargs)
    
    def get_metadata(
        self,
        source: Any,
        format: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get metadata for any supported format"""
        if format is None:
            format = self.detect_format(source)
        
        if format is None:
            return {"error": "Could not detect format"}
        
        handler = self._handlers.get(format)
        if handler is None:
            return {"error": f"No handler for format: {format}"}
        
        return handler.get_metadata(source)
    
    def to_format(
        self,
        data: Any,
        target_format: str,
        **kwargs,
    ) -> Any:
        """Convert data to target format"""
        # Read data
        import pandas as pd
        df = pd.DataFrame() if isinstance(data, pd.DataFrame) else data
        
        # Write to buffer
        buffer = io.BytesIO()
        self.write(df, buffer, target_format, **kwargs)
        buffer.seek(0)
        
        return buffer.getvalue()
    
    @property
    def supported_formats(self) -> List[str]:
        """List supported formats"""
        return list(self._handlers.keys())
    
    @property
    def object_storage(self) -> ObjectStorageHandler:
        """Get object storage handler"""
        return self._object_storage
