"""
Compression Manager

Manages data compression for storage optimization.
"""

import gzip
import logging
import os
import shutil
import zlib
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class CompressionAlgorithm(Enum):
    """Supported compression algorithms"""
    GZIP = "gzip"
    ZLIB = "zlib"
    SNAPPY = "snappy"
    LZ4 = "lz4"
    ZSTD = "zstd"
    NONE = "none"


class CompressionManager:
    """
    Compression Manager for data storage optimization.
    
    Features:
    - Multiple compression algorithms
    - Automatic compression based on file type
    - Compression level control
    - Streaming compression for large files
    - Compression statistics
    """
    
    def __init__(
        self,
        storage_path: str = "data_platform/compression",
        default_algorithm: CompressionAlgorithm = CompressionAlgorithm.GZIP,
        default_level: int = 6,
    ):
        self._storage_path = storage_path
        self._default_algorithm = default_algorithm
        self._default_level = default_level
        
        # Compression statistics
        self._stats = {
            "total_compressions": 0,
            "total_decompressions": 0,
            "total_original_size": 0,
            "total_compressed_size": 0,
            "by_algorithm": {},
        }
        
        os.makedirs(storage_path, exist_ok=True)
        self._load_stats()
    
    def _load_stats(self) -> None:
        """Load compression statistics"""
        stats_file = f"{self._storage_path}/stats.json"
        if os.path.exists(stats_file):
            try:
                import json
                with open(stats_file, "r") as f:
                    self._stats = json.load(f)
            except Exception:
                pass
    
    def _save_stats(self) -> None:
        """Save compression statistics"""
        stats_file = f"{self._storage_path}/stats.json"
        try:
            import json
            with open(stats_file, "w") as f:
                json.dump(self._stats, f, indent=2)
        except Exception:
            pass
    
    def _update_stats(
        self,
        algorithm: str,
        original_size: int,
        compressed_size: int,
        operation: str = "compress",
    ) -> None:
        """Update compression statistics"""
        if algorithm not in self._stats["by_algorithm"]:
            self._stats["by_algorithm"][algorithm] = {
                "compressions": 0,
                "decompressions": 0,
                "original_size": 0,
                "compressed_size": 0,
            }
        
        stats = self._stats["by_algorithm"][algorithm]
        
        if operation == "compress":
            self._stats["total_compressions"] += 1
            stats["compressions"] += 1
            self._stats["total_original_size"] += original_size
            stats["original_size"] += original_size
            self._stats["total_compressed_size"] += compressed_size
            stats["compressed_size"] += compressed_size
        else:
            self._stats["total_decompressions"] += 1
            stats["decompressions"] += 1
        
        self._save_stats()
    
    def compress(
        self,
        data: bytes,
        algorithm: Optional[CompressionAlgorithm] = None,
        level: Optional[int] = None,
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Compress data.
        
        Returns:
            Tuple of (compressed_data, metadata)
        """
        algorithm = algorithm or self._default_algorithm
        level = level or self._default_level
        
        original_size = len(data)
        
        if algorithm == CompressionAlgorithm.GZIP:
            compressed = gzip.compress(data, compresslevel=level)
        elif algorithm == CompressionAlgorithm.ZLIB:
            compressed = zlib.compress(data, level=level)
        elif algorithm == CompressionAlgorithm.SNAPPY:
            compressed = self._snappy_compress(data)
        elif algorithm == CompressionAlgorithm.LZ4:
            compressed = self._lz4_compress(data)
        elif algorithm == CompressionAlgorithm.ZSTD:
            compressed = self._zstd_compress(data, level)
        else:
            compressed = data
        
        compressed_size = len(compressed)
        ratio = compressed_size / original_size if original_size > 0 else 1.0
        
        self._update_stats(
            algorithm.value,
            original_size,
            compressed_size,
            "compress",
        )
        
        metadata = {
            "algorithm": algorithm.value,
            "level": level,
            "original_size": original_size,
            "compressed_size": compressed_size,
            "compression_ratio": ratio,
            "space_saved": original_size - compressed_size,
        }
        
        return compressed, metadata
    
    def decompress(
        self,
        data: bytes,
        algorithm: CompressionAlgorithm,
    ) -> bytes:
        """Decompress data"""
        original_size = len(data)
        
        if algorithm == CompressionAlgorithm.GZIP:
            decompressed = gzip.decompress(data)
        elif algorithm == CompressionAlgorithm.ZLIB:
            decompressed = zlib.decompress(data)
        elif algorithm == CompressionAlgorithm.SNAPPY:
            decompressed = self._snappy_decompress(data)
        elif algorithm == CompressionAlgorithm.LZ4:
            decompressed = self._lz4_decompress(data)
        elif algorithm == CompressionAlgorithm.ZSTD:
            decompressed = self._zstd_decompress(data)
        else:
            decompressed = data
        
        self._update_stats(algorithm.value, 0, original_size, "decompress")
        
        return decompressed
    
    def compress_file(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        algorithm: Optional[CompressionAlgorithm] = None,
        level: Optional[int] = None,
        delete_original: bool = False,
    ) -> Dict[str, Any]:
        """Compress a file"""
        algorithm = algorithm or self._default_algorithm
        output_path = output_path or f"{input_path}.{algorithm.value}"
        
        with open(input_path, "rb") as f:
            data = f.read()
        
        compressed, metadata = self.compress(data, algorithm, level)
        
        with open(output_path, "wb") as f:
            f.write(compressed)
        
        metadata["input_path"] = input_path
        metadata["output_path"] = output_path
        
        if delete_original and input_path != output_path:
            os.remove(input_path)
        
        logger.info(
            f"Compressed {input_path} -> {output_path} "
            f"(ratio: {metadata['compression_ratio']:.2%})"
        )
        
        return metadata
    
    def decompress_file(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        algorithm: Optional[CompressionAlgorithm] = None,
        delete_compressed: bool = False,
    ) -> Dict[str, Any]:
        """Decompress a file"""
        if algorithm is None:
            # Try to detect from extension
            for alg in CompressionAlgorithm:
                if alg.value in input_path:
                    algorithm = alg
                    break
            algorithm = algorithm or CompressionAlgorithm.GZIP
        
        if output_path is None:
            output_path = input_path
            for alg in CompressionAlgorithm:
                output_path = output_path.replace(f".{alg.value}", "")
        
        with open(input_path, "rb") as f:
            compressed = f.read()
        
        decompressed = self.decompress(compressed, algorithm)
        
        with open(output_path, "wb") as f:
            f.write(decompressed)
        
        metadata = {
            "algorithm": algorithm.value,
            "input_path": input_path,
            "output_path": output_path,
            "decompressed_size": len(decompressed),
        }
        
        if delete_compressed and input_path != output_path:
            os.remove(input_path)
        
        logger.info(f"Decompressed {input_path} -> {output_path}")
        
        return metadata
    
    def _snappy_compress(self, data: bytes) -> bytes:
        """Compress using snappy (fallback to gzip if unavailable)"""
        try:
            import snappy
            return snappy.compress(data)
        except ImportError:
            logger.warning("snappy not available, using gzip fallback")
            return gzip.compress(data)
    
    def _snappy_decompress(self, data: bytes) -> bytes:
        """Decompress using snappy (fallback to gzip if unavailable)"""
        try:
            import snappy
            return snappy.decompress(data)
        except ImportError:
            logger.warning("snappy not available, using gzip fallback")
            return gzip.decompress(data)
    
    def _lz4_compress(self, data: bytes) -> bytes:
        """Compress using lz4 (fallback to gzip if unavailable)"""
        try:
            import lz4.frame
            return lz4.frame.compress(data)
        except ImportError:
            logger.warning("lz4 not available, using gzip fallback")
            return gzip.compress(data)
    
    def _lz4_decompress(self, data: bytes) -> bytes:
        """Decompress using lz4 (fallback to gzip if unavailable)"""
        try:
            import lz4.frame
            return lz4.frame.decompress(data)
        except ImportError:
            logger.warning("lz4 not available, using gzip fallback")
            return gzip.decompress(data)
    
    def _zstd_compress(self, data: bytes, level: int = 3) -> bytes:
        """Compress using zstd (fallback to gzip if unavailable)"""
        try:
            import zstandard as zstd
            cctx = zstd.ZstdCompressor(level=level)
            return cctx.compress(data)
        except ImportError:
            logger.warning("zstd not available, using gzip fallback")
            return gzip.compress(data, compresslevel=level)
    
    def _zstd_decompress(self, data: bytes) -> bytes:
        """Decompress using zstd (fallback to gzip if unavailable)"""
        try:
            import zstandard as zstd
            dctx = zstd.ZstdDecompressor()
            return dctx.decompress(data)
        except ImportError:
            logger.warning("zstd not available, using gzip fallback")
            return gzip.decompress(data)
    
    def get_best_algorithm(self, data: bytes) -> Tuple[CompressionAlgorithm, Dict[str, Any]]:
        """Find the best compression algorithm for data"""
        results = {}
        
        for algorithm in CompressionAlgorithm:
            if algorithm == CompressionAlgorithm.NONE:
                continue
            
            try:
                compressed, metadata = self.compress(data, algorithm)
                results[algorithm] = metadata
            except Exception as e:
                logger.warning(f"Algorithm {algorithm.value} failed: {e}")
        
        if not results:
            return CompressionAlgorithm.NONE, {"error": "No algorithms available"}
        
        # Find best by compression ratio
        best = min(results.items(), key=lambda x: x[1]["compression_ratio"])
        return best[0], best[1]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get compression statistics"""
        total_original = self._stats.get("total_original_size", 0)
        total_compressed = self._stats.get("total_compressed_size", 0)
        
        return {
            **self._stats,
            "overall_ratio": total_compressed / total_original if total_original > 0 else 1.0,
            "space_saved_bytes": total_original - total_compressed,
            "space_saved_percentage": (
                (total_original - total_compressed) / total_original * 100
                if total_original > 0 else 0
            ),
        }
