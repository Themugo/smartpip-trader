"""
Strategy Marketplace

A marketplace for discovering, installing, and managing trading strategy plugins with:
- Plugin metadata and descriptions
- Performance metrics and ratings
- Version management
- Compatibility checks
- Installation and update workflows
"""

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

# Optional semver for version comparison
try:
    import semver
    SEMVER_AVAILABLE = True
except ImportError:
    SEMVER_AVAILABLE = False
    # Fallback semver functions
    def is_compatible(version: str, other: str) -> bool:
        return version.split('.')[0] == other.split('.')[0]
    
    def compare(v1: str, v2: str) -> int:
        parts1 = [int(p) for p in v1.split('.')]
        parts2 = [int(p) for p in v2.split('.')]
        for p1, p2 in zip(parts1, parts2):
            if p1 < p2:
                return -1
            elif p1 > p2:
                return 1
        return 0

from plugins.base import PluginMetadata, PerformanceMetrics

logger = logging.getLogger(__name__)


class MarketplaceStatus(Enum):
    """Plugin installation status"""
    AVAILABLE = "available"
    INSTALLED = "installed"
    UPDATE_AVAILABLE = "update_available"
    INCOMPATIBLE = "incompatible"
    INSTALLING = "installing"
    UPDATING = "updating"
    UNINSTALLING = "uninstalling"
    ERROR = "error"


class CompatibilityLevel(Enum):
    """Compatibility level with platform version"""
    FULL = "full"
    PARTIAL = "partial"
    DEPRECATED = "deprecated"
    INCOMPATIBLE = "incompatible"


@dataclass
class MarketplaceListing:
    """Complete marketplace listing for a plugin"""
    metadata: PluginMetadata
    status: MarketplaceStatus = MarketplaceStatus.AVAILABLE
    compatibility: CompatibilityLevel = CompatibilityLevel.FULL
    compatibility_notes: List[str] = field(default_factory=list)
    installed_version: Optional[str] = None
    rating: float = 0.0
    review_count: int = 0
    downloads: int = 0
    last_tested: Optional[datetime] = None
    changelog: List[str] = field(default_factory=list)
    screenshots: List[str] = field(default_factory=list)
    source_url: Optional[str] = None
    bundle_size: Optional[int] = None  # bytes
    checksum: Optional[str] = None
    installation_path: Optional[str] = None
    requires_restart: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "status": self.status.value,
            "compatibility": self.compatibility.value,
            "compatibility_notes": self.compatibility_notes,
            "installed_version": self.installed_version,
            "rating": self.rating,
            "review_count": self.review_count,
            "downloads": self.downloads,
            "last_tested": self.last_tested.isoformat() if self.last_tested else None,
            "changelog": self.changelog,
            "screenshots": self.screenshots,
            "source_url": self.source_url,
            "bundle_size": self.bundle_size,
            "checksum": self.checksum,
            "installation_path": self.installation_path,
            "requires_restart": self.requires_restart,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MarketplaceListing":
        data = data.copy()
        if "metadata" in data:
            data["metadata"] = PluginMetadata.from_dict(data["metadata"])
        if "status" in data:
            data["status"] = MarketplaceStatus(data["status"])
        if "compatibility" in data:
            data["compatibility"] = CompatibilityLevel(data["compatibility"])
        if "last_tested" in data and data["last_tested"]:
            data["last_tested"] = datetime.fromisoformat(data["last_tested"])
        return cls(**data)
    
    @property
    def needs_update(self) -> bool:
        return self.status == MarketplaceStatus.UPDATE_AVAILABLE
    
    @property
    def is_installed(self) -> bool:
        return self.status in (MarketplaceStatus.INSTALLED, MarketplaceStatus.UPDATE_AVAILABLE)


@dataclass
class CompatibilityResult:
    """Result of compatibility check"""
    level: CompatibilityLevel
    notes: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    can_install: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "notes": self.notes,
            "issues": self.issues,
            "warnings": self.warnings,
            "can_install": self.can_install,
        }


class StrategyMarketplace:
    """
    Manages the strategy marketplace including:
    - Plugin discovery and browsing
    - Installation and updates
    - Version compatibility checking
    - Performance metrics aggregation
    - User preferences and favorites
    """
    
    PLATFORM_VERSION = "1.0.0"
    MIN_API_VERSION = "1.0.0"
    
    def __init__(self, storage_path: Optional[str] = None):
        self._storage_path = storage_path or "data/marketplace"
        self._listings: Dict[str, MarketplaceListing] = {}
        self._installed: Dict[str, MarketplaceListing] = {}
        self._favorites: List[str] = []
        self._platform_plugins: Dict[str, str] = {}  # plugin_id -> version
        self._load_marketplace_data()
    
    def _load_marketplace_data(self) -> None:
        """Load marketplace data from storage"""
        import os
        data_file = os.path.join(self._storage_path, "marketplace.json")
        
        if os.path.exists(data_file):
            try:
                with open(data_file, "r") as f:
                    data = json.load(f)
                    for listing_data in data.get("listings", []):
                        listing = MarketplaceListing.from_dict(listing_data)
                        self._listings[listing.metadata.id] = listing
                    
                    self._favorites = data.get("favorites", [])
                    self._platform_plugins = data.get("platform_plugins", {})
            except Exception as e:
                logger.error(f"Failed to load marketplace data: {e}")
    
    def _save_marketplace_data(self) -> None:
        """Save marketplace data to storage"""
        import os
        os.makedirs(self._storage_path, exist_ok=True)
        data_file = os.path.join(self._storage_path, "marketplace.json")
        
        try:
            with open(data_file, "w") as f:
                json.dump({
                    "listings": [l.to_dict() for l in self._listings.values()],
                    "favorites": self._favorites,
                    "platform_plugins": self._platform_plugins,
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save marketplace data: {e}")
    
    def register_platform_version(self, plugin_id: str, version: str) -> None:
        """Register a platform-built-in plugin version"""
        self._platform_plugins[plugin_id] = version
    
    def check_compatibility(
        self,
        plugin_api_version: str,
        plugin_metadata: PluginMetadata,
    ) -> CompatibilityResult:
        """
        Check if a plugin is compatible with the current platform.
        
        Args:
            plugin_api_version: The API version the plugin was built for
            plugin_metadata: The plugin metadata
            
        Returns:
            CompatibilityResult with compatibility details
        """
        issues = []
        warnings = []
        notes = []
        can_install = True
        
        # Check API version compatibility
        try:
            if not is_compatible(plugin_api_version, self.MIN_API_VERSION):
                # Check if we can do a minor version check
                try:
                    api_parts = plugin_api_version.split(".")
                    min_parts = self.MIN_API_VERSION.split(".")
                    api_major = int(api_parts[0])
                    min_major = int(min_parts[0])
                    
                    if api_major > min_major:
                        issues.append(
                            f"Plugin requires API version {plugin_api_version}, "
                            f"but platform supports up to {self.MIN_API_VERSION}"
                        )
                        can_install = False
                    elif api_parts[0] == min_parts[0]:
                        # Same major version, likely compatible
                        notes.append(f"API version {plugin_api_version} is compatible")
                    else:
                        warnings.append(
                            f"Plugin API version {plugin_api_version} is older than "
                            f"platform minimum {self.MIN_API_VERSION}"
                        )
                except Exception:
                    warnings.append(f"Could not validate API version {plugin_api_version}")
        except Exception as e:
            warnings.append(f"Version comparison failed: {e}")
        
        # Check dependencies
        for dep in plugin_metadata.dependencies:
            if dep not in self._platform_plugins:
                issues.append(f"Missing dependency: {dep}")
                can_install = False
        
        # Check market compatibility
        if plugin_metadata.supported_markets:
            supported = ["R_10", "R_25", "R_50", "R_75", "R_100"]
            for market in plugin_metadata.supported_markets:
                if market not in supported:
                    warnings.append(f"Market {market} may not be available")
        
        # Determine compatibility level
        if not can_install:
            level = CompatibilityLevel.INCOMPATIBLE
        elif issues:
            level = CompatibilityLevel.PARTIAL
            warnings.extend(issues)
        elif warnings:
            level = CompatibilityLevel.PARTIAL
        elif compare(plugin_api_version, self.PLATFORM_VERSION) == 0:
            level = CompatibilityLevel.FULL
            notes.append("Plugin is fully compatible with platform")
        else:
            level = CompatibilityLevel.DEPRECATED
            warnings.append("Plugin may be outdated")
        
        return CompatibilityResult(
            level=level,
            notes=notes,
            issues=issues,
            warnings=warnings,
            can_install=can_install,
        )
    
    def add_listing(self, listing: MarketplaceListing) -> bool:
        """
        Add a plugin to the marketplace.
        
        Args:
            listing: The marketplace listing to add
            
        Returns:
            True if added successfully
        """
        # Check compatibility
        compat = self.check_compatibility(
            listing.metadata.api_version,
            listing.metadata,
        )
        listing.compatibility = compat.level
        listing.compatibility_notes = compat.notes + compat.warnings
        
        self._listings[listing.metadata.id] = listing
        self._save_marketplace_data()
        logger.info(f"Added listing to marketplace: {listing.metadata.name}")
        return True
    
    def remove_listing(self, plugin_id: str) -> bool:
        """Remove a plugin from the marketplace"""
        if plugin_id in self._listings:
            del self._listings[plugin_id]
            self._save_marketplace_data()
            return True
        return False
    
    def get_listing(self, plugin_id: str) -> Optional[MarketplaceListing]:
        """Get a specific marketplace listing"""
        return self._listings.get(plugin_id)
    
    def get_all_listings(
        self,
        status: Optional[MarketplaceStatus] = None,
        tags: Optional[List[str]] = None,
        search_query: Optional[str] = None,
        sort_by: str = "downloads",
        reverse: bool = True,
    ) -> List[MarketplaceListing]:
        """
        Get marketplace listings with filtering and sorting.
        
        Args:
            status: Filter by installation status
            tags: Filter by tags (any match)
            search_query: Search in name and description
            sort_by: Field to sort by (downloads, rating, name)
            reverse: Sort in descending order
            
        Returns:
            Filtered and sorted list of listings
        """
        results = list(self._listings.values())
        
        # Apply filters
        if status:
            results = [l for l in results if l.status == status]
        
        if tags:
            results = [
                l for l in results 
                if any(tag in l.metadata.tags for tag in tags)
            ]
        
        if search_query:
            query = search_query.lower()
            results = [
                l for l in results
                if query in l.metadata.name.lower() or 
                   query in l.metadata.description.lower()
            ]
        
        # Apply sorting
        sort_key = {
            "downloads": lambda l: l.downloads,
            "rating": lambda l: l.rating,
            "name": lambda l: l.metadata.name.lower(),
            "date": lambda l: l.metadata.updated_at,
        }.get(sort_by, lambda l: l.downloads)
        
        results.sort(key=sort_key, reverse=reverse)
        
        return results
    
    def search_listings(
        self,
        query: str,
        max_results: int = 20,
    ) -> List[MarketplaceListing]:
        """
        Search marketplace listings.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            Matching listings
        """
        query_lower = query.lower()
        scored = []
        
        for listing in self._listings.values():
            score = 0
            name_lower = listing.metadata.name.lower()
            desc_lower = listing.metadata.description.lower()
            
            # Exact match in name
            if query_lower == name_lower:
                score = 100
            # Starts with query
            elif name_lower.startswith(query_lower):
                score = 80
            # Contains query in name
            elif query_lower in name_lower:
                score = 60
            # Contains query in description
            elif query_lower in desc_lower:
                score = 40
            # Matches tags
            elif any(query_lower in tag.lower() for tag in listing.metadata.tags):
                score = 30
            
            if score > 0:
                scored.append((score, listing))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return [l for _, l in scored[:max_results]]
    
    def install_plugin(
        self,
        plugin_id: str,
        version: Optional[str] = None,
    ) -> bool:
        """
        Mark a plugin as installed.
        
        Args:
            plugin_id: Plugin to install
            version: Specific version to install (latest if None)
            
        Returns:
            True if successful
        """
        listing = self._listings.get(plugin_id)
        if not listing:
            logger.error(f"Plugin {plugin_id} not found in marketplace")
            return False
        
        compat = self.check_compatibility(
            listing.metadata.api_version,
            listing.metadata,
        )
        
        if not compat.can_install:
            logger.error(f"Plugin {plugin_id} is not compatible: {compat.issues}")
            listing.status = MarketplaceStatus.INCOMPATIBLE
            self._save_marketplace_data()
            return False
        
        listing.status = MarketplaceStatus.INSTALLED
        listing.installed_version = version or listing.metadata.version
        self._installed[plugin_id] = listing
        self._save_marketplace_data()
        
        logger.info(f"Installed plugin: {plugin_id} (version {listing.installed_version})")
        return True
    
    def uninstall_plugin(self, plugin_id: str) -> bool:
        """
        Uninstall a plugin.
        
        Args:
            plugin_id: Plugin to uninstall
            
        Returns:
            True if successful
        """
        listing = self._listings.get(plugin_id)
        if not listing:
            return False
        
        if plugin_id in self._platform_plugins:
            logger.warning(f"Cannot uninstall platform plugin: {plugin_id}")
            return False
        
        listing.status = MarketplaceStatus.AVAILABLE
        listing.installed_version = None
        self._installed.pop(plugin_id, None)
        self._save_marketplace_data()
        
        logger.info(f"Uninstalled plugin: {plugin_id}")
        return True
    
    def update_plugin(self, plugin_id: str, new_version: str) -> bool:
        """
        Update a plugin to a new version.
        
        Args:
            plugin_id: Plugin to update
            new_version: New version to install
            
        Returns:
            True if successful
        """
        listing = self._listings.get(plugin_id)
        if not listing or listing.status not in (
            MarketplaceStatus.INSTALLED,
            MarketplaceStatus.UPDATE_AVAILABLE,
        ):
            return False
        
        # Validate new version
        try:
            if not compare(new_version, listing.metadata.version) > 0:
                logger.error(f"New version {new_version} is not newer than current")
                return False
        except Exception:
            logger.warning(f"Could not validate version comparison for {new_version}")
        
        listing.installed_version = new_version
        listing.status = MarketplaceStatus.INSTALLED
        self._installed[plugin_id] = listing
        self._save_marketplace_data()
        
        logger.info(f"Updated plugin {plugin_id} to version {new_version}")
        return True
    
    def check_updates(self) -> List[MarketplaceListing]:
        """
        Check for available updates for installed plugins.
        
        Returns:
            List of plugins with updates available
        """
        updates = []
        
        for plugin_id, listing in self._installed.items():
            # Check if newer version is available
            # In a real implementation, this would check against a remote registry
            try:
                if compare(
                    listing.metadata.version,
                    listing.installed_version or "0.0.0"
                ) > 0:
                    listing.status = MarketplaceStatus.UPDATE_AVAILABLE
                    updates.append(listing)
            except Exception:
                pass
        
        self._save_marketplace_data()
        return updates
    
    def get_installed(self) -> List[MarketplaceListing]:
        """Get all installed plugins"""
        return list(self._installed.values())
    
    def get_categories(self) -> Dict[str, int]:
        """Get plugin count by category/tags"""
        categories: Dict[str, int] = {}
        for listing in self._listings.values():
            for tag in listing.metadata.tags:
                categories[tag] = categories.get(tag, 0) + 1
        return categories
    
    def add_to_favorites(self, plugin_id: str) -> bool:
        """Add a plugin to favorites"""
        if plugin_id not in self._favorites:
            self._favorites.append(plugin_id)
            self._save_marketplace_data()
            return True
        return False
    
    def remove_from_favorites(self, plugin_id: str) -> bool:
        """Remove a plugin from favorites"""
        if plugin_id in self._favorites:
            self._favorites.remove(plugin_id)
            self._save_marketplace_data()
            return True
        return False
    
    def get_favorites(self) -> List[MarketplaceListing]:
        """Get favorite plugins"""
        return [
            self._listings[pid] 
            for pid in self._favorites 
            if pid in self._listings
        ]
    
    def update_metrics(
        self,
        plugin_id: str,
        metrics: PerformanceMetrics,
    ) -> bool:
        """
        Update performance metrics for a plugin.
        
        Args:
            plugin_id: Plugin to update
            metrics: New metrics
            
        Returns:
            True if successful
        """
        listing = self._listings.get(plugin_id)
        if not listing:
            return False
        
        # Recalculate rating based on metrics
        if metrics.total_trades > 0:
            win_rate_factor = metrics.win_rate / 100
            profit_factor = min(metrics.profit_factor / 2, 1.0)  # Cap at 2.0
            listing.rating = (win_rate_factor * 0.6 + profit_factor * 0.4) * 5
        
        self._save_marketplace_data()
        return True
    
    def record_download(self, plugin_id: str) -> None:
        """Record a download for a plugin"""
        listing = self._listings.get(plugin_id)
        if listing:
            listing.downloads += 1
            self._save_marketplace_data()
    
    def validate_checksum(self, plugin_id: str, data: bytes) -> bool:
        """
        Validate plugin bundle checksum.
        
        Args:
            plugin_id: Plugin to validate
            data: Downloaded bundle data
            
        Returns:
            True if checksum matches
        """
        listing = self._listings.get(plugin_id)
        if not listing or not listing.checksum:
            return True  # No checksum to validate
        
        actual = hashlib.sha256(data).hexdigest()
        return actual == listing.checksum
    
    def export_config(self) -> Dict[str, Any]:
        """Export marketplace configuration"""
        return {
            "installed": [
                {
                    "plugin_id": pid,
                    "version": l.installed_version,
                    "path": l.installation_path,
                }
                for pid, l in self._installed.items()
            ],
            "favorites": self._favorites,
            "platform_version": self.PLATFORM_VERSION,
        }
    
    def import_config(self, config: Dict[str, Any]) -> None:
        """Import marketplace configuration"""
        for item in config.get("installed", []):
            plugin_id = item["plugin_id"]
            version = item.get("version")
            
            if plugin_id in self._listings:
                self.install_plugin(plugin_id, version)
        
        self._favorites = config.get("favorites", [])
        self._save_marketplace_data()


def create_marketplace(storage_path: Optional[str] = None) -> StrategyMarketplace:
    """Factory function to create a strategy marketplace"""
    return StrategyMarketplace(storage_path=storage_path)
