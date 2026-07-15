"""
Replay Exporter
==============

Export replay sessions in various formats.
"""

import csv
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TextIO
from uuid import uuid4

logger = logging.getLogger(__name__)


class ExportFormat(Enum):
    """Export formats"""
    JSON = "json"
    CSV = "csv"
    MARKDOWN = "markdown"
    HTML = "html"
    BINARY = "binary"


@dataclass
class ExportOptions:
    """Export options"""
    format: ExportFormat = ExportFormat.JSON
    include_metadata: bool = True
    include_bookmarks: bool = True
    include_annotations: bool = True
    compress: bool = False
    pretty_print: bool = True
    max_events: Optional[int] = None  # Limit events for large exports


class ReplayExporter:
    """
    Export replay sessions in various formats.
    
    Supports:
    - JSON (full fidelity)
    - CSV (tabular format)
    - Markdown (human readable)
    - HTML (interactive viewer)
    """
    
    def __init__(self, output_dir: str = "data/replay/exports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def export_session(
        self,
        session: Any,
        options: ExportOptions = None
    ) -> str:
        """
        Export a replay session.
        
        Args:
            session: ReplaySession to export
            options: Export options
            
        Returns:
            Path to exported file
        """
        options = options or ExportOptions()
        
        if options.format == ExportFormat.JSON:
            return self._export_json(session, options)
        elif options.format == ExportFormat.CSV:
            return self._export_csv(session, options)
        elif options.format == ExportFormat.MARKDOWN:
            return self._export_markdown(session, options)
        elif options.format == ExportFormat.HTML:
            return self._export_html(session, options)
        else:
            raise ValueError(f"Unsupported format: {options.format}")
    
    def _export_json(
        self,
        session: Any,
        options: ExportOptions
    ) -> str:
        """Export as JSON"""
        filename = f"{session.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path = os.path.join(self.output_dir, filename)
        
        # Build export data
        events = session.events
        if options.max_events:
            events = events[:options.max_events]
        
        export_data = {
            "session_info": {
                "session_id": session.session_id,
                "name": session.name,
                "start_time": session.start_time.isoformat(),
                "end_time": session.end_time.isoformat(),
                "duration_seconds": session.duration.total_seconds(),
                "event_count": len(events)
            },
            "events": [e.to_dict() for e in events],
            "metadata": {
                "exported_at": datetime.now().isoformat(),
                "version": "1.0"
            }
        }
        
        if options.include_bookmarks:
            export_data["bookmarks"] = session.bookmarks
        
        if options.include_annotations:
            export_data["annotations"] = session.annotations
        
        # Write file
        with open(path, 'w') as f:
            if options.pretty_print:
                json.dump(export_data, f, indent=2)
            else:
                json.dump(export_data, f)
        
        logger.info(f"Exported JSON: {path}")
        return path
    
    def _export_csv(
        self,
        session: Any,
        options: ExportOptions
    ) -> str:
        """Export as CSV"""
        filename = f"{session.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path = os.path.join(self.output_dir, filename)
        
        events = session.events
        if options.max_events:
            events = events[:options.max_events]
        
        with open(path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                "event_id", "timestamp", "sequence", "event_type",
                "data", "deterministic_hash"
            ])
            
            # Events
            for event in events:
                writer.writerow([
                    event.event_id,
                    event.timestamp.isoformat(),
                    event.sequence,
                    event.event_type.value,
                    json.dumps(event.data),
                    event.deterministic_hash
                ])
        
        logger.info(f"Exported CSV: {path}")
        return path
    
    def _export_markdown(
        self,
        session: Any,
        options: ExportOptions
    ) -> str:
        """Export as Markdown"""
        filename = f"{session.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        path = os.path.join(self.output_dir, filename)
        
        events = session.events
        if options.max_events:
            events = events[:options.max_events]
        
        lines = [
            f"# Replay Session: {session.name}",
            "",
            f"**Session ID:** {session.session_id}",
            f"**Start:** {session.start_time.isoformat()}",
            f"**End:** {session.end_time.isoformat()}",
            f"**Duration:** {session.duration}",
            f"**Events:** {len(events)}",
            "",
            "---",
            "",
            "## Event Timeline",
            ""
        ]
        
        # Group events by type
        by_type: Dict[str, List[Any]] = {}
        for event in events:
            etype = event.event_type.value
            if etype not in by_type:
                by_type[etype] = []
            by_type[etype].append(event)
        
        # Write by type
        for etype, type_events in sorted(by_type.items()):
            lines.append(f"### {etype.replace('_', ' ').title()} ({len(type_events)})")
            lines.append("")
            
            for event in type_events[:50]:  # Limit per type
                lines.append(f"- **{event.timestamp.strftime('%H:%M:%S.%f')}** `{event.event_id[:8]}`: {self._summarize_event(event)}")
            
            if len(type_events) > 50:
                lines.append(f"  ... and {len(type_events) - 50} more")
            
            lines.append("")
        
        # Bookmarks
        if options.include_bookmarks and session.bookmarks:
            lines.extend([
                "---",
                "",
                "## Bookmarks",
                ""
            ])
            
            for bookmark_id, description in session.bookmarks.items():
                lines.append(f"- [{bookmark_id[:8]}] {description}")
            
            lines.append("")
        
        # Annotations
        if options.include_annotations and session.annotations:
            lines.extend([
                "---",
                "",
                "## Annotations",
                ""
            ])
            
            for annotation in session.annotations:
                ts = annotation.get("timestamp", "")
                text = annotation.get("annotation", "")
                category = annotation.get("category", "general")
                lines.append(f"- [{ts}] *({category})* {text}")
            
            lines.append("")
        
        # Summary
        lines.extend([
            "---",
            "",
            "## Summary Statistics",
            "",
            "| Event Type | Count |",
            "|-----------|-------|"
        ])
        
        for etype, type_events in sorted(by_type.items(), key=lambda x: len(x[1]), reverse=True):
            lines.append(f"| {etype} | {len(type_events)} |")
        
        lines.extend([
            "",
            f"*Exported: {datetime.now().isoformat()}*"
        ])
        
        with open(path, 'w') as f:
            f.write("\n".join(lines))
        
        logger.info(f"Exported Markdown: {path}")
        return path
    
    def _export_html(
        self,
        session: Any,
        options: ExportOptions
    ) -> str:
        """Export as HTML"""
        filename = f"{session.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        path = os.path.join(self.output_dir, filename)
        
        events = session.events
        if options.max_events:
            events = events[:options.max_events]
        
        # Build HTML
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Replay: {session.name}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #1a1a2e; color: #eee; }}
        .header {{ background: #16213e; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .stats {{ display: flex; gap: 20px; flex-wrap: wrap; }}
        .stat {{ background: #0f3460; padding: 10px 20px; border-radius: 4px; }}
        .stat-value {{ font-size: 24px; font-weight: bold; color: #e94560; }}
        .stat-label {{ font-size: 12px; color: #888; }}
        .timeline {{ background: #16213e; border-radius: 8px; padding: 20px; }}
        .event {{ padding: 10px; border-left: 3px solid #e94560; margin: 5px 0; background: #0f3460; border-radius: 0 4px 4px 0; }}
        .event-time {{ color: #888; font-size: 12px; }}
        .event-type {{ color: #e94560; font-weight: bold; }}
        .event-data {{ font-family: monospace; font-size: 12px; margin-top: 5px; color: #aaa; }}
        .filter {{ margin-bottom: 20px; }}
        .filter select {{ padding: 10px; background: #0f3460; color: #fff; border: none; border-radius: 4px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Replay Session: {session.name}</h1>
        <div class="stats">
            <div class="stat">
                <div class="stat-value">{len(events)}</div>
                <div class="stat-label">Events</div>
            </div>
            <div class="stat">
                <div class="stat-value">{session.duration}</div>
                <div class="stat-label">Duration</div>
            </div>
            <div class="stat">
                <div class="stat-value">{session.start_time.strftime('%Y-%m-%d')}</div>
                <div class="stat-label">Date</div>
            </div>
        </div>
    </div>
    
    <div class="filter">
        <select onchange="filterEvents(this.value)">
            <option value="all">All Events</option>
            <option value="tick">Market Data</option>
            <option value="strategy_decision">Strategy Decisions</option>
            <option value="ai_confidence">AI Events</option>
            <option value="risk_check">Risk Checks</option>
            <option value="trade_entry">Trade Entry</option>
            <option value="trade_exit">Trade Exit</option>
        </select>
    </div>
    
    <div class="timeline" id="timeline">
"""
        
        for event in events:
            html += f"""
        <div class="event" data-type="{event.event_type.value}">
            <div class="event-time">{event.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')}</div>
            <div class="event-type">{event.event_type.value}</div>
            <div class="event-data">{json.dumps(event.data)[:200]}...</div>
        </div>
"""
        
        html += """
    </div>
    
    <script>
        function filterEvents(type) {
            const events = document.querySelectorAll('.event');
            events.forEach(event => {
                if (type === 'all' || event.dataset.type === type) {
                    event.style.display = 'block';
                } else {
                    event.style.display = 'none';
                }
            });
        }
    </script>
</body>
</html>
"""
        
        with open(path, 'w') as f:
            f.write(html)
        
        logger.info(f"Exported HTML: {path}")
        return path
    
    def _summarize_event(self, event: Any) -> str:
        """Create a summary of an event"""
        data = event.data
        
        if event.event_type.value == "tick":
            return f"{data.get('symbol', '?')} {data.get('bid', 0):.5f}/{data.get('ask', 0):.5f}"
        elif event.event_type.value == "strategy_decision":
            return f"{data.get('action', '?')} {data.get('confidence', 0):.2%}"
        elif event.event_type.value == "ai_confidence":
            return f"Conf: {data.get('confidence', 0):.2%}"
        elif event.event_type.value == "risk_check":
            return f"{data.get('check_name', '?')}: {data.get('result', '?')}"
        elif event.event_type.value == "trade_entry":
            return f"{data.get('symbol', '?')} {data.get('direction', '?')} {data.get('size', 0)}"
        elif event.event_type.value == "trade_exit":
            return f"PnL: {data.get('pnl', 0):.2f}"
        else:
            return str(data)[:50]
    
    def import_session(
        self,
        path: str,
        format: ExportFormat = None
    ) -> Any:
        """
        Import a replay session from file.
        
        Args:
            path: Path to import from
            format: Import format (auto-detected if None)
            
        Returns:
            ReplaySession
        """
        from .core import ReplaySession, ReplayEvent
        
        if format is None:
            if path.endswith('.json'):
                format = ExportFormat.JSON
            elif path.endswith('.csv'):
                format = ExportFormat.CSV
            else:
                raise ValueError("Cannot auto-detect format")
        
        if format == ExportFormat.JSON:
            return self._import_json(path)
        else:
            raise ValueError(f"Import not supported for {format}")
    
    def _import_json(self, path: str) -> Any:
        """Import from JSON"""
        from .core import ReplaySession, ReplayEvent
        
        with open(path, 'r') as f:
            data = json.load(f)
        
        session_info = data["session_info"]
        events = [ReplayEvent.from_dict(e) for e in data["events"]]
        
        session = ReplaySession(
            session_id=session_info["session_id"],
            name=session_info["name"],
            start_time=datetime.fromisoformat(session_info["start_time"]),
            end_time=datetime.fromisoformat(session_info["end_time"]),
            events=events,
            bookmarks=data.get("bookmarks", {}),
            annotations=data.get("annotations", [])
        )
        
        logger.info(f"Imported session: {session.session_id}")
        return session
    
    def get_export_history(self) -> List[Dict[str, Any]]:
        """Get history of exports"""
        exports = []
        
        for filename in os.listdir(self.output_dir):
            path = os.path.join(self.output_dir, filename)
            stat = os.stat(path)
            
            exports.append({
                "filename": filename,
                "path": path,
                "size_bytes": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat()
            })
        
        return sorted(exports, key=lambda x: x["created_at"], reverse=True)
