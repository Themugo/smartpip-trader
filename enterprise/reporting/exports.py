"""
Export Utilities

Export reports to various formats:
- PDF
- Excel (XLSX)
- CSV
"""

import csv
import io
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path


class PDFExporter:
    """
    Export reports to PDF format.
    """
    
    def __init__(self, template_dir: Optional[str] = None):
        self._template_dir = template_dir
    
    def export(
        self,
        data: Dict[str, Any],
        title: str,
        output_path: Optional[str] = None,
    ) -> bytes:
        """
        Export data to PDF.
        
        Returns PDF bytes or writes to output_path.
        """
        # In production, use WeasyPrint, ReportLab, or similar
        # For now, return HTML as bytes
        html = self._generate_html(data, title)
        
        if output_path:
            Path(output_path).write_bytes(html)
            return b""
        
        return html
    
    def _generate_html(self, data: Dict[str, Any], title: str) -> bytes:
        """Generate HTML for PDF conversion"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{title}</title>
            <style>
                @page {{
                    size: A4;
                    margin: 2cm;
                }}
                body {{
                    font-family: 'Helvetica Neue', Arial, sans-serif;
                    font-size: 11pt;
                    line-height: 1.6;
                    color: #333;
                }}
                h1 {{
                    font-size: 24pt;
                    color: #1a365d;
                    border-bottom: 2px solid #3B82F6;
                    padding-bottom: 10px;
                }}
                h2 {{
                    font-size: 16pt;
                    color: #2d3748;
                    margin-top: 20px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 15px 0;
                }}
                th {{
                    background: #3B82F6;
                    color: white;
                    padding: 10px;
                    text-align: left;
                }}
                td {{
                    padding: 8px 10px;
                    border-bottom: 1px solid #e2e8f0;
                }}
                tr:nth-child(even) {{
                    background: #f7fafc;
                }}
                .metric-card {{
                    display: inline-block;
                    padding: 15px 25px;
                    margin: 10px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border-radius: 8px;
                    color: white;
                }}
                .metric-value {{
                    font-size: 24pt;
                    font-weight: bold;
                }}
                .metric-label {{
                    font-size: 10pt;
                    opacity: 0.9;
                }}
                .footer {{
                    position: fixed;
                    bottom: 0;
                    width: 100%;
                    text-align: center;
                    font-size: 9pt;
                    color: #718096;
                    border-top: 1px solid #e2e8f0;
                    padding-top: 10px;
                }}
            </style>
        </head>
        <body>
            <h1>{title}</h1>
            <p style="color: #718096; font-size: 10pt;">
                Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC
            </p>
            
            {self._render_content(data)}
            
            <div class="footer">
                SmartPip Trader Enterprise Platform | Confidential
            </div>
        </body>
        </html>
        """
        return html.encode('utf-8')
    
    def _render_content(self, data: Dict[str, Any]) -> str:
        """Render data content as HTML"""
        html = ""
        
        # Summary section
        if "summary" in data:
            html += "<h2>Summary</h2><div>"
            for key, value in data["summary"].items():
                html += f'''
                <div class="metric-card">
                    <div class="metric-value">{value}</div>
                    <div class="metric-label">{key.replace("_", " ").title()}</div>
                </div>
                '''
            html += "</div>"
        
        # Performance section
        if "performance" in data:
            perf = data["performance"]
            html += "<h2>Performance Metrics</h2><table><tr><th>Metric</th><th>Value</th></tr>"
            for key, value in perf.items():
                html += f"<tr><td>{key.replace('_', ' ').title()}</td><td>{value}</td></tr>"
            html += "</table>"
        
        # Trades section
        if "trades" in data:
            html += "<h2>Trade Journal</h2><table><tr>"
            if data["trades"]:
                for key in data["trades"][0].keys():
                    html += f"<th>{key.replace('_', ' ').title()}</th>"
            html += "</tr>"
            for trade in data["trades"][:50]:  # Limit to 50 trades
                html += "<tr>"
                for value in trade.values():
                    html += f"<td>{value}</td>"
                html += "</tr>"
            html += "</table>"
        
        # Tables
        for section_name in ["top_strategies", "market_summary", "strategy_breakdown"]:
            if section_name in data:
                html += f"<h2>{section_name.replace('_', ' ').title()}</h2><table><tr>"
                items = data[section_name]
                if items:
                    for key in items[0].keys():
                        html += f"<th>{key.replace('_', ' ').title()}</th>"
                    html += "</tr>"
                    for item in items:
                        html += "<tr>"
                        for value in item.values():
                            html += f"<td>{value}</td>"
                        html += "</tr>"
                html += "</table>"
        
        return html


class ExcelExporter:
    """
    Export reports to Excel format.
    """
    
    def __init__(self):
        self._sheets: Dict[str, List[Dict[str, Any]]] = {}
    
    def add_sheet(self, name: str, data: List[Dict[str, Any]]) -> "ExcelExporter":
        """Add a sheet with data"""
        self._sheets[name] = data
        return self
    
    def export(self, output_path: Optional[str] = None) -> bytes:
        """
        Export to Excel format.
        
        Returns XLSX bytes or writes to output_path.
        """
        # In production, use openpyxl
        # For now, return CSV representation
        output = io.BytesIO()
        
        with io.TextIOWrapper(output, encoding='utf-8', write_through=True) as f:
            writer = csv.writer(f)
            
            for sheet_name, data in self._sheets.items():
                f.write(f"=== {sheet_name} ===\n")
                
                if data:
                    # Header
                    writer.writerow(data[0].keys())
                    
                    # Rows
                    for row in data:
                        writer.writerow(row.values())
                
                f.write("\n")
        
        if output_path:
            Path(output_path).write_bytes(output.getvalue())
            return b""
        
        return output.getvalue()
    
    def export_report(self, report_data: Dict[str, Any], title: str) -> bytes:
        """Export complete report to Excel"""
        self._sheets = {}
        
        # Summary sheet
        if "summary" in report_data:
            self.add_sheet("Summary", [report_data["summary"]])
        
        # Performance sheet
        if "performance" in report_data:
            perf = [{"metric": k, "value": v} for k, v in report_data["performance"].items()]
            self.add_sheet("Performance", perf)
        
        # Trades sheet
        if "trades" in report_data:
            self.add_sheet("Trades", report_data["trades"])
        
        # Strategies sheet
        if "top_strategies" in report_data:
            self.add_sheet("Strategies", report_data["top_strategies"])
        
        return self.export()


class CSVExporter:
    """
    Export data to CSV format.
    """
    
    def __init__(
        self,
        delimiter: str = ",",
        quotechar: str = '"',
        encoding: str = "utf-8",
    ):
        self._delimiter = delimiter
        self._quotechar = quotechar
        self._encoding = encoding
    
    def export(
        self,
        data: List[Dict[str, Any]],
        output_path: Optional[str] = None,
        include_header: bool = True,
    ) -> str:
        """
        Export data to CSV format.
        
        Returns CSV string or writes to output_path.
        """
        if not data:
            return ""
        
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=data[0].keys(),
            delimiter=self._delimiter,
            quotechar=self._quotechar,
        )
        
        if include_header:
            writer.writeheader()
        
        writer.writerows(data)
        
        csv_content = output.getvalue()
        
        if output_path:
            Path(output_path).write_text(csv_content, encoding=self._encoding)
            return ""
        
        return csv_content
    
    def export_multiple(
        self,
        sheets: Dict[str, List[Dict[str, Any]]],
        output_path: Optional[str] = None,
    ) -> str:
        """Export multiple datasets as CSV (sheet separated by ===)"""
        output = io.StringIO()
        
        for sheet_name, data in sheets.items():
            output.write(f"=== {sheet_name} ===\n")
            
            if data:
                writer = csv.DictWriter(
                    output,
                    fieldnames=data[0].keys(),
                    delimiter=self._delimiter,
                )
                writer.writeheader()
                writer.writerows(data)
            
            output.write("\n")
        
        csv_content = output.getvalue()
        
        if output_path:
            Path(output_path).write_text(csv_content, encoding=self._encoding)
            return ""
        
        return csv_content


class ExportManager:
    """
    Unified export manager.
    """
    
    def __init__(self):
        self._pdf_exporter = PDFExporter()
        self._excel_exporter = ExcelExporter()
        self._csv_exporter = CSVExporter()
    
    def export(
        self,
        data: Dict[str, Any],
        format: str,
        title: str,
        output_path: Optional[str] = None,
    ) -> bytes:
        """
        Export data to specified format.
        
        Args:
            data: Report data
            format: Export format (pdf, xlsx, csv, json, html)
            title: Report title
            output_path: Optional path to write file
        
        Returns:
            Exported file bytes
        """
        format = format.lower()
        
        if format == "pdf":
            return self._pdf_exporter.export(data, title, output_path)
        elif format == "xlsx" or format == "excel":
            return self._excel_exporter.export_report(data, title)
        elif format == "csv":
            # Flatten data for CSV
            flat_data = [data]
            return self._csv_exporter.export(flat_data, output_path)
        elif format == "json":
            json_str = json.dumps(data, indent=2, default=str)
            if output_path:
                Path(output_path).write_text(json_str)
                return b""
            return json_str.encode('utf-8')
        elif format == "html":
            html = f"<html><head><title>{title}</title></head><body><pre>{json.dumps(data, indent=2)}</pre></body></html>"
            if output_path:
                Path(output_path).write_text(html)
                return b""
            return html.encode('utf-8')
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported export formats"""
        return ["pdf", "xlsx", "csv", "json", "html"]
    
    def get_mime_type(self, format: str) -> str:
        """Get MIME type for format"""
        mime_types = {
            "pdf": "application/pdf",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "csv": "text/csv",
            "json": "application/json",
            "html": "text/html",
        }
        return mime_types.get(format.lower(), "application/octet-stream")
