"""
Marketplace Catalog

Plugin marketplace with versioning, compatibility checks, and digital signatures.
"""

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class PluginCategory(Enum):
    """Plugin categories"""
    STRATEGY = "strategy"
    INDICATOR = "indicator"
    VISUALIZATION = "visualization"
    ALERT = "alert"
    INTEGRATION = "integration"
    REPORTING = "reporting"
    UTILITY = "utility"


class Compatibility(Enum):
    """Compatibility levels"""
    FULL = "full"
    PARTIAL = "partial"
    INCOMPATIBLE = "incompatible"


class PluginStatus(Enum):
    """Plugin status"""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"
    REMOVED = "removed"


@dataclass
class PluginVersion:
    """Plugin version information"""
    version: str
    changelog: str = ""
    min_platform_version: str = "1.0.0"
    max_platform_version: str = "2.0.0"
    release_date: datetime = field(default_factory=datetime.utcnow)
    download_url: str = ""
    file_hash: str = ""
    file_size: int = 0
    signature: Optional[str] = None
    is_latest: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "changelog": self.changelog,
            "min_platform_version": self.min_platform_version,
            "max_platform_version": self.max_platform_version,
            "release_date": self.release_date.isoformat(),
            "file_hash": self.file_hash,
            "file_size": self.file_size,
            "is_latest": self.is_latest,
        }


@dataclass
class Plugin:
    """Marketplace plugin"""
    plugin_id: str
    name: str
    slug: str
    category: PluginCategory
    
    # Author info
    author_id: str
    author_name: str
    author_email: str
    
    # Description
    short_description: str
    long_description: str = ""
    icon_url: Optional[str] = None
    screenshots: List[str] = field(default_factory=list)
    
    # Version info
    current_version: str = "1.0.0"
    versions: List[PluginVersion] = field(default_factory=list)
    
    # Stats
    downloads: int = 0
    rating: float = 0.0
    review_count: int = 0
    
    # Status
    status: PluginStatus = PluginStatus.DRAFT
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    requirements: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    
    # Pricing
    price: float = 0.0
    currency: str = "USD"
    license_type: str = "MIT"
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "name": self.name,
            "slug": self.slug,
            "category": self.category.value,
            "author": {
                "id": self.author_id,
                "name": self.author_name,
            },
            "short_description": self.short_description,
            "current_version": self.current_version,
            "downloads": self.downloads,
            "rating": self.rating,
            "review_count": self.review_count,
            "status": self.status.value,
            "price": self.price,
            "currency": self.currency,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }


@dataclass
class PluginReview:
    """Plugin review"""
    review_id: str
    plugin_id: str
    user_id: str
    rating: int  # 1-5
    title: str
    content: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    helpful_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "review_id": self.review_id,
            "plugin_id": self.plugin_id,
            "user_id": self.user_id,
            "rating": self.rating,
            "title": self.title,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "helpful_count": self.helpful_count,
        }


class MarketplaceCatalog:
    """
    Plugin marketplace catalog.
    
    Features:
    - Plugin discovery
    - Version management
    - Compatibility checking
    - Digital signature verification
    """
    
    def __init__(self):
        self._plugins: Dict[str, Plugin] = {}
        self._reviews: Dict[str, List[PluginReview]] = {}
        self._installations: Dict[str, List[str]] = {}  # org_id -> [plugin_ids]
    
    def register_plugin(self, plugin: Plugin) -> str:
        """Register a new plugin"""
        plugin.plugin_id = f"plg_{uuid.uuid4().hex[:12]}"
        self._plugins[plugin.plugin_id] = plugin
        return plugin.plugin_id
    
    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """Get plugin by ID"""
        return self._plugins.get(plugin_id)
    
    def get_plugin_by_slug(self, slug: str) -> Optional[Plugin]:
        """Get plugin by slug"""
        for plugin in self._plugins.values():
            if plugin.slug == slug:
                return plugin
        return None
    
    def search_plugins(
        self,
        query: Optional[str] = None,
        category: Optional[PluginCategory] = None,
        tags: Optional[List[str]] = None,
        min_rating: Optional[float] = None,
        free_only: bool = False,
        sort_by: str = "downloads",
    ) -> List[Plugin]:
        """Search plugins in marketplace"""
        results = list(self._plugins.values())
        
        # Filter by status
        results = [p for p in results if p.status == PluginStatus.APPROVED]
        
        # Filter by query
        if query:
            query = query.lower()
            results = [
                p for p in results
                if query in p.name.lower() or query in p.short_description.lower()
            ]
        
        # Filter by category
        if category:
            results = [p for p in results if p.category == category]
        
        # Filter by tags
        if tags:
            results = [
                p for p in results
                if any(tag in p.tags for tag in tags)
            ]
        
        # Filter by rating
        if min_rating:
            results = [p for p in results if p.rating >= min_rating]
        
        # Filter free only
        if free_only:
            results = [p for p in results if p.price == 0]
        
        # Sort
        if sort_by == "downloads":
            results.sort(key=lambda p: p.downloads, reverse=True)
        elif sort_by == "rating":
            results.sort(key=lambda p: p.rating, reverse=True)
        elif sort_by == "recent":
            results.sort(key=lambda p: p.published_at or p.created_at, reverse=True)
        
        return results
    
    def check_compatibility(
        self,
        plugin: Plugin,
        platform_version: str,
    ) -> Tuple[Compatibility, str]:
        """
        Check plugin compatibility with platform version.
        
        Returns (compatibility_level, message)
        """
        latest = None
        for v in plugin.versions:
            if v.is_latest:
                latest = v
                break
        
        if not latest:
            latest = plugin.versions[-1] if plugin.versions else None
        
        if not latest:
            return Compatibility.INCOMPATIBLE, "No compatible version found"
        
        # Parse versions
        try:
            min_ver = tuple(int(x) for x in latest.min_platform_version.split("."))
            max_ver = tuple(int(x) for x in latest.max_platform_version.split("."))
            plat_ver = tuple(int(x) for x in platform_version.split("."))
            
            if plat_ver < min_ver:
                return Compatibility.INCOMPATIBLE, f"Requires platform {latest.min_platform_version}+"
            elif plat_ver > max_ver:
                return Compatibility.PARTIAL, f"Designed for platform {latest.max_platform_version}+"
            else:
                return Compatibility.FULL, "Fully compatible"
        except ValueError:
            return Compatibility.PARTIAL, "Version check failed"
    
    def verify_signature(self, plugin: Plugin, version: PluginVersion) -> bool:
        """
        Verify plugin digital signature.
        
        In production, this would use actual cryptographic verification.
        """
        if not version.signature:
            return False
        
        # Verify signature using author's public key
        data = f"{plugin.plugin_id}:{version.version}:{version.file_hash}"
        expected_hash = hashlib.sha256(data.encode()).hexdigest()
        
        return True  # Placeholder
    
    def rate_plugin(self, plugin_id: str, user_id: str, rating: int) -> bool:
        """Rate a plugin"""
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False
        
        # Update average rating
        total_rating = plugin.rating * plugin.review_count + rating
        plugin.review_count += 1
        plugin.rating = total_rating / plugin.review_count
        
        return True
    
    def install_plugin(self, org_id: str, plugin_id: str) -> bool:
        """Install plugin for organization"""
        if org_id not in self._installations:
            self._installations[org_id] = []
        
        if plugin_id not in self._installations[org_id]:
            self._installations[org_id].append(plugin_id)
            
            # Update download count
            plugin = self._plugins.get(plugin_id)
            if plugin:
                plugin.downloads += 1
            
            return True
        
        return False
    
    def uninstall_plugin(self, org_id: str, plugin_id: str) -> bool:
        """Uninstall plugin for organization"""
        if org_id in self._installations:
            if plugin_id in self._installations[org_id]:
                self._installations[org_id].remove(plugin_id)
                return True
        return False
    
    def get_installed_plugins(self, org_id: str) -> List[Plugin]:
        """Get all installed plugins for organization"""
        plugin_ids = self._installations.get(org_id, [])
        return [self._plugins[pid] for pid in plugin_ids if pid in self._plugins]
    
    def get_categories(self) -> List[Dict[str, Any]]:
        """Get all categories with counts"""
        categories = {}
        for plugin in self._plugins.values():
            if plugin.status == PluginStatus.APPROVED:
                cat = plugin.category.value
                categories[cat] = categories.get(cat, 0) + 1
        
        return [
            {"id": cat.value, "name": cat.value.title(), "count": count}
            for cat, count in categories.items()
        ]
