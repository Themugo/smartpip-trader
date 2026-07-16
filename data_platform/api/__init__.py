"""
Data Platform API Routes

REST API for the SmartPip Data Platform.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)


def create_data_platform_routes(data_lake) -> Blueprint:
    """
    Create Data Platform API routes.
    
    Args:
        data_lake: DataLake instance
    
    Returns:
        Flask Blueprint
    """
    bp = Blueprint("data_platform", __name__, url_prefix="/api/v1/data")
    
    # ==================== Health & Status ====================
    
    @bp.route("/health", methods=["GET"])
    def health():
        """Health check endpoint"""
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
        })
    
    @bp.route("/statistics", methods=["GET"])
    def statistics():
        """Get comprehensive statistics"""
        try:
            stats = data_lake.get_statistics()
            return jsonify(stats)
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return jsonify({"error": str(e)}), 500
    
    # ==================== Dataset Operations ====================
    
    @bp.route("/datasets", methods=["GET"])
    def list_datasets():
        """List all datasets"""
        try:
            validated_only = request.args.get("validated_only", "true").lower() == "true"
            datasets = data_lake.registry.list_datasets(validated_only=validated_only)
            return jsonify({
                "datasets": datasets,
                "total": len(datasets),
            })
        except Exception as e:
            logger.error(f"Error listing datasets: {e}")
            return jsonify({"error": str(e)}), 500
    
    @bp.route("/datasets", methods=["POST"])
    def ingest_dataset():
        """Ingest a new dataset"""
        try:
            data = request.json
            if not data:
                return jsonify({"error": "No data provided"}), 400
            
            # Extract parameters
            dataset, metadata = data_lake.ingest(
                data=data.get("data"),
                name=data.get("name"),
                description=data.get("description", ""),
                market=data.get("market", ""),
                source=data.get("source", "live"),
                source_uri=data.get("source_uri", ""),
                symbols=data.get("symbols"),
                format=data.get("format", "parquet"),
                owner=data.get("owner", ""),
                team=data.get("team", ""),
                tags=data.get("tags", []),
            )
            
            return jsonify({
                "dataset": dataset.to_dict(),
                "metadata": metadata,
            }), 201
        except Exception as e:
            logger.error(f"Error ingesting dataset: {e}")
            return jsonify({"error": str(e)}), 500
    
    @bp.route("/datasets/<dataset_id>", methods=["GET"])
    def get_dataset(dataset_id: str):
        """Get a dataset by ID"""
        try:
            dataset = data_lake.get_dataset(dataset_id)
            if not dataset:
                return jsonify({"error": "Dataset not found"}), 404
            
            return jsonify(dataset.to_dict())
        except Exception as e:
            logger.error(f"Error getting dataset: {e}")
            return jsonify({"error": str(e)}), 500
    
    @bp.route("/datasets/<dataset_id>", methods=["PUT"])
    def update_dataset(dataset_id: str):
        """Update dataset metadata"""
        try:
            data = request.json
            if not data:
                return jsonify({"error": "No data provided"}), 400
            
            dataset = data_lake.registry.update_dataset(
                dataset_id=dataset_id,
                **data,
            )
            
            if not dataset:
                return jsonify({"error": "Dataset not found"}), 404
            
            return jsonify(dataset.to_dict())
        except Exception as e:
            logger.error(f"Error updating dataset: {e}")
            return jsonify({"error": str(e)}), 500
    
    @bp.route("/datasets/<dataset_id>/data", methods=["GET"])
    def read_dataset(dataset_id: str):
        """Read dataset content"""
        try:
            version = request.args.get("version")
            as_of = request.args.get("as_of")
            
            if as_of:
                as_of = datetime.fromisoformat(as_of)
            
            data = data_lake.read(dataset_id, version=version, as_of=as_of)
            if data is None:
                return jsonify({"error": "Dataset not found"}), 404
            
            return jsonify({
                "dataset_id": dataset_id,
                "data": data.to_dict() if hasattr(data, "to_dict") else data,
            })
        except Exception as e:
            logger.error(f"Error reading dataset: {e}")
            return jsonify({"error": str(e)}), 500
    
    @bp.route("/datasets/<dataset_id>/validate", methods=["POST"])
    def validate_dataset(dataset_id: str):
        """Validate a dataset"""
        try:
            level = request.args.get("level", "standard")
            
            result = data_lake.validate_dataset(dataset_id, level=level)
            if result is None:
                return jsonify({"error": "Dataset not found"}), 404
            
            return jsonify(result.to_dict())
        except Exception as e:
            logger.error(f"Error validating dataset: {e}")
            return jsonify({"error": str(e)}), 500
    
    @bp.route("/datasets/<dataset_id>/versions", methods=["GET"])
    def get_versions(dataset_id: str):
        """Get version history"""
        try:
            versions = data_lake.get_version_history(dataset_id)
            return jsonify({
                "dataset_id": dataset_id,
                "versions": versions,
            })
        except Exception as e:
            logger.error(f"Error getting versions: {e}")
            return jsonify({"error": str(e)}), 500
    
    @bp.route("/datasets/<dataset_id>/lineage", methods=["GET"])
    def get_lineage(dataset_id: str):
        """Get dataset lineage"""
        try:
            lineage = data_lake.get_lineage(dataset_id)
            return jsonify(lineage)
        except Exception as e:
            logger.error(f"Error getting lineage: {e}")
            return jsonify({"error": str(e)}), 500
    
    # ==================== Feature Operations ====================
    
    @bp.route("/features", methods=["GET"])
    def list_features():
        """List all features"""
        try:
            features = data_lake.features.list_features()
            return jsonify({
                "features": features,
                "total": len(features),
            })
        except Exception as e:
            logger.error(f"Error listing features: {e}")
            return jsonify({"error": str(e)}), 500
    
    @bp.route("/features", methods=["POST"])
    def register_feature():
        """Register a new feature"""
        try:
            data = request.json
            if not data:
                return jsonify({"error": "No data provided"}), 400
            
            feature, is_new = data_lake.register_feature(
                name=data.get("name"),
                description=data.get("description", ""),
                feature_type=data.get("feature_type", "derived"),
                dependencies=data.get("dependencies", []),
                **data,
            )
            
            return jsonify({
                "feature": feature.to_dict(),
                "is_new": is_new,
            }), 201
        except Exception as e:
            logger.error(f"Error registering feature: {e}")
            return jsonify({"error": str(e)}), 500
    
    @bp.route("/features/<feature_id>", methods=["GET"])
    def get_feature(feature_id: str):
        """Get a feature by ID"""
        try:
            feature = data_lake.features.get_feature(feature_id)
            if not feature:
                return jsonify({"error": "Feature not found"}), 404
            
            return jsonify(feature.to_dict())
        except Exception as e:
            logger.error(f"Error getting feature: {e}")
            return jsonify({"error": str(e)}), 500
    
    @bp.route("/features/<feature_id>/lineage", methods=["GET"])
    def get_feature_lineage(feature_id: str):
        """Get feature lineage"""
        try:
            lineage = data_lake.features.get_feature_lineage(feature_id)
            return jsonify(lineage)
        except Exception as e:
            logger.error(f"Error getting feature lineage: {e}")
            return jsonify({"error": str(e)}), 500
    
    @bp.route("/features/<feature_id>/usage", methods=["POST"])
    def record_feature_usage(feature_id: str):
        """Record feature usage"""
        try:
            data = request.json
            if not data:
                return jsonify({"error": "No data provided"}), 400
            
            usage = data_lake.features.record_usage(
                feature_id=feature_id,
                used_by=data.get("used_by", ""),
                use_case=data.get("use_case", ""),
                dataset_id=data.get("dataset_id", ""),
                performance_impact=data.get("performance_impact"),
            )
            
            if not usage:
                return jsonify({"error": "Feature not found"}), 404
            
            return jsonify(usage.to_dict())
        except Exception as e:
            logger.error(f"Error recording feature usage: {e}")
            return jsonify({"error": str(e)}), 500
    
    # ==================== Schema Operations ====================
    
    @bp.route("/schemas", methods=["GET"])
    def list_schemas():
        """List all schemas"""
        try:
            schemas = data_lake.schema_registry.search_schemas()
            return jsonify({
                "schemas": schemas,
                "total": len(schemas),
            })
        except Exception as e:
            logger.error(f"Error listing schemas: {e}")
            return jsonify({"error": str(e)}), 500
    
    @bp.route("/schemas", methods=["POST"])
    def register_schema():
        """Register a new schema"""
        try:
            data = request.json
            if not data:
                return jsonify({"error": "No data provided"}), 400
            
            schema = data_lake.register_schema(
                name=data.get("name"),
                fields=data.get("fields", []),
                **data,
            )
            
            return jsonify(schema.to_dict()), 201
        except Exception as e:
            logger.error(f"Error registering schema: {e}")
            return jsonify({"error": str(e)}), 500
    
    @bp.route("/schemas/<registry_id>/validate", methods=["POST"])
    def validate_against_schema(registry_id: str):
        """Validate data against a schema"""
        try:
            data = request.json.get("data", [])
            is_valid, errors, summary = data_lake.validate_against_schema(
                registry_id=registry_id,
                data=data,
            )
            
            return jsonify({
                "is_valid": is_valid,
                "errors": errors,
                "summary": summary,
            })
        except Exception as e:
            logger.error(f"Error validating against schema: {e}")
            return jsonify({"error": str(e)}), 500
    
    # ==================== Search Operations ====================
    
    @bp.route("/search", methods=["GET"])
    def search():
        """Search across all data assets"""
        try:
            query = request.args.get("q", "")
            entity_type = request.args.get("type")  # dataset, feature, schema
            
            if entity_type == "dataset":
                results = data_lake.catalog.search_datasets(query=query)
            elif entity_type == "feature":
                results = data_lake.catalog.search_features(query=query)
            else:
                # Search all
                results = data_lake.catalog.search(query=query)
            
            return jsonify({
                "query": query,
                "results": [r.to_dict() for r in results],
                "total": len(results),
            })
        except Exception as e:
            logger.error(f"Error searching: {e}")
            return jsonify({"error": str(e)}), 500
    
    # ==================== Integrity Operations ====================
    
    @bp.route("/integrity/verify/<dataset_id>", methods=["POST"])
    def verify_integrity(dataset_id: str):
        """Verify dataset integrity"""
        try:
            result = data_lake.verify_integrity(dataset_id)
            if result is None:
                return jsonify({"error": "Dataset not found"}), 404
            
            return jsonify(result.to_dict())
        except Exception as e:
            logger.error(f"Error verifying integrity: {e}")
            return jsonify({"error": str(e)}), 500
    
    @bp.route("/integrity/checks", methods=["GET"])
    def get_pending_checks():
        """Get pending integrity checks"""
        try:
            pending = data_lake.integrity.get_pending_checks()
            return jsonify({
                "pending": [{"dataset_id": did, "last_check": lc.isoformat()} for did, lc in pending],
                "total": len(pending),
            })
        except Exception as e:
            logger.error(f"Error getting pending checks: {e}")
            return jsonify({"error": str(e)}), 500
    
    @bp.route("/integrity/manifest", methods=["GET"])
    def generate_manifest():
        """Generate integrity manifest"""
        try:
            manifest = data_lake.integrity.generate_manifest()
            return jsonify(manifest)
        except Exception as e:
            logger.error(f"Error generating manifest: {e}")
            return jsonify({"error": str(e)}), 500
    
    # ==================== Maintenance Operations ====================
    
    @bp.route("/maintenance/cleanup", methods=["POST"])
    def cleanup():
        """Run maintenance cleanup tasks"""
        try:
            results = {
                "snapshots_cleaned": data_lake.cleanup_expired_snapshots(),
                "archives_processed": data_lake.process_archives(),
                "integrity_checks": len(data_lake.run_integrity_checks()),
            }
            
            return jsonify(results)
        except Exception as e:
            logger.error(f"Error running cleanup: {e}")
            return jsonify({"error": str(e)}), 500
    
    # ==================== Catalog Operations ====================
    
    @bp.route("/catalog", methods=["GET"])
    def get_catalog():
        """Get metadata catalog"""
        try:
            stats = data_lake.catalog.get_statistics()
            popular = data_lake.catalog.get_popular(limit=10)
            recent = data_lake.catalog.get_recent(limit=10)
            
            return jsonify({
                "statistics": stats,
                "popular": [e.to_dict() for e in popular],
                "recent": [e.to_dict() for e in recent],
            })
        except Exception as e:
            logger.error(f"Error getting catalog: {e}")
            return jsonify({"error": str(e)}), 500
    
    return bp


def register_data_platform(app, data_lake):
    """
    Register Data Platform routes with Flask app.
    
    Args:
        app: Flask application
        data_lake: DataLake instance
    """
    from flask import Flask
    
    bp = create_data_platform_routes(data_lake)
    app.register_blueprint(bp)
    
    logger.info("Data Platform routes registered")
