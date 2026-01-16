"""
PRISMA 2020 Flow Diagram Generator for ScholaRAG_Graph.

Generates PRISMA 2020 compliant flow diagrams for systematic literature reviews.
Based on: Page MJ, et al. BMJ 2021;372:n71
http://www.prisma-statement.org/

Security Note:
All user-provided strings are sanitized using html.escape() before
embedding in SVG/HTML output to prevent XSS attacks.
"""

import html
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


def _sanitize(value: str) -> str:
    """
    Sanitize user input for safe embedding in SVG/HTML.

    Escapes HTML special characters to prevent XSS attacks.
    """
    if not isinstance(value, str):
        return str(value)
    return html.escape(value, quote=True)


class OutputFormat(str, Enum):
    """Output format for PRISMA diagram."""
    SVG = "svg"
    HTML = "html"
    JSON = "json"
    MERMAID = "mermaid"


@dataclass
class PRISMAStatistics:
    """Statistics for PRISMA 2020 flow diagram."""
    
    # Identification
    records_identified_databases: int = 0
    records_identified_registers: int = 0
    records_identified_other: int = 0
    
    # Identification sources (for breakdown)
    database_sources: Dict[str, int] = field(default_factory=dict)
    # e.g., {"Semantic Scholar": 500, "OpenAlex": 300, "arXiv": 200}
    
    # Duplicates
    duplicates_removed: int = 0
    
    # Screening
    records_screened: int = 0
    records_excluded_screening: int = 0
    
    # Eligibility (Full-text)
    reports_sought: int = 0
    reports_not_retrieved: int = 0
    reports_assessed: int = 0
    reports_excluded: int = 0
    exclusion_reasons: Dict[str, int] = field(default_factory=dict)
    # e.g., {"Wrong population": 10, "Wrong intervention": 5, "Wrong outcome": 3}
    
    # Included
    studies_included: int = 0
    reports_included: int = 0
    
    # Optional: Previous studies (for updated reviews)
    previous_studies: int = 0
    previous_reports: int = 0
    
    @property
    def total_identified(self) -> int:
        """Total records identified from all sources."""
        return (
            self.records_identified_databases +
            self.records_identified_registers +
            self.records_identified_other
        )
    
    @property
    def after_deduplication(self) -> int:
        """Records remaining after deduplication."""
        return self.total_identified - self.duplicates_removed
    
    def validate(self) -> list[str]:
        """Validate statistics for consistency."""
        errors = []
        
        if self.records_screened > self.after_deduplication:
            errors.append("Records screened exceeds records after deduplication")
        
        if self.records_excluded_screening > self.records_screened:
            errors.append("Records excluded exceeds records screened")
        
        if self.reports_assessed > (self.records_screened - self.records_excluded_screening):
            errors.append("Reports assessed exceeds eligible records")
        
        if self.studies_included > self.reports_assessed:
            errors.append("Studies included exceeds reports assessed")
        
        return errors


class PRISMAGenerator:
    """
    PRISMA 2020 Flow Diagram Generator.
    
    Generates flow diagrams following the PRISMA 2020 statement guidelines.
    """
    
    # PRISMA 2020 color scheme
    COLORS = {
        "identification": "#E3F2FD",  # Light blue
        "screening": "#FFF3E0",       # Light orange
        "eligibility": "#E8F5E9",     # Light green
        "included": "#F3E5F5",        # Light purple
        "border": "#424242",          # Dark gray
        "text": "#212121",            # Almost black
        "arrow": "#757575",           # Medium gray
    }
    
    def __init__(self, stats: PRISMAStatistics, title: Optional[str] = None):
        """
        Initialize PRISMA generator.
        
        Args:
            stats: PRISMA statistics
            title: Optional title for the diagram
        """
        self.stats = stats
        self.title = title or "PRISMA 2020 Flow Diagram"
    
    def generate(self, format: OutputFormat = OutputFormat.SVG) -> str:
        """
        Generate PRISMA diagram in specified format.
        
        Args:
            format: Output format (svg, html, json, mermaid)
            
        Returns:
            Diagram in specified format
        """
        if format == OutputFormat.SVG:
            return self._generate_svg()
        elif format == OutputFormat.HTML:
            return self._generate_html()
        elif format == OutputFormat.JSON:
            return self._generate_json()
        elif format == OutputFormat.MERMAID:
            return self._generate_mermaid()
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _generate_svg(self) -> str:
        """Generate SVG format PRISMA diagram."""
        s = self.stats
        
        # SVG dimensions
        width = 900
        height = 800
        
        svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
  <defs>
    <style>
      .box {{ fill: white; stroke: {self.COLORS["border"]}; stroke-width: 1.5; }}
      .box-id {{ fill: {self.COLORS["identification"]}; }}
      .box-screen {{ fill: {self.COLORS["screening"]}; }}
      .box-elig {{ fill: {self.COLORS["eligibility"]}; }}
      .box-inc {{ fill: {self.COLORS["included"]}; }}
      .title {{ font-family: Arial, sans-serif; font-size: 18px; font-weight: bold; fill: {self.COLORS["text"]}; }}
      .label {{ font-family: Arial, sans-serif; font-size: 11px; fill: {self.COLORS["text"]}; }}
      .label-bold {{ font-weight: bold; }}
      .number {{ font-family: Arial, sans-serif; font-size: 13px; font-weight: bold; fill: {self.COLORS["text"]}; }}
      .section {{ font-family: Arial, sans-serif; font-size: 14px; font-weight: bold; fill: {self.COLORS["text"]}; }}
      .arrow {{ fill: none; stroke: {self.COLORS["arrow"]}; stroke-width: 1.5; marker-end: url(#arrowhead); }}
    </style>
    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="{self.COLORS["arrow"]}" />
    </marker>
  </defs>
  
  <!-- Title -->
  <text x="{width//2}" y="30" text-anchor="middle" class="title">{_sanitize(self.title)}</text>
  
  <!-- IDENTIFICATION Section -->
  <text x="30" y="70" class="section">Identification</text>
  
  <!-- Records from databases -->
  <rect x="50" y="90" width="250" height="80" rx="5" class="box box-id" />
  <text x="175" y="115" text-anchor="middle" class="label label-bold">Records identified from databases</text>
  <text x="175" y="135" text-anchor="middle" class="number">(n = {s.records_identified_databases})</text>
  <text x="175" y="155" text-anchor="middle" class="label">{self._format_sources()}</text>
  
  <!-- Records from other sources -->
  <rect x="350" y="90" width="250" height="80" rx="5" class="box box-id" />
  <text x="475" y="115" text-anchor="middle" class="label label-bold">Records from other sources</text>
  <text x="475" y="135" text-anchor="middle" class="number">(n = {s.records_identified_registers + s.records_identified_other})</text>
  
  <!-- Duplicates removed -->
  <rect x="650" y="90" width="200" height="80" rx="5" class="box" />
  <text x="750" y="120" text-anchor="middle" class="label label-bold">Duplicates removed</text>
  <text x="750" y="145" text-anchor="middle" class="number">(n = {s.duplicates_removed})</text>
  
  <!-- Arrow from databases to duplicates -->
  <path d="M 300 130 L 650 130" class="arrow" />
  <path d="M 475 170 L 475 200 L 600 200 L 600 130 L 650 130" class="arrow" style="marker-end: none;" />
  
  <!-- SCREENING Section -->
  <text x="30" y="230" class="section">Screening</text>
  
  <!-- Records screened -->
  <rect x="150" y="250" width="250" height="70" rx="5" class="box box-screen" />
  <text x="275" y="280" text-anchor="middle" class="label label-bold">Records screened</text>
  <text x="275" y="300" text-anchor="middle" class="number">(n = {s.records_screened})</text>
  
  <!-- Records excluded -->
  <rect x="500" y="250" width="200" height="70" rx="5" class="box" />
  <text x="600" y="280" text-anchor="middle" class="label label-bold">Records excluded</text>
  <text x="600" y="300" text-anchor="middle" class="number">(n = {s.records_excluded_screening})</text>
  
  <!-- Arrow from screening to excluded -->
  <path d="M 400 285 L 500 285" class="arrow" />
  
  <!-- Arrow down from identification -->
  <path d="M 275 170 L 275 250" class="arrow" />
  
  <!-- ELIGIBILITY Section -->
  <text x="30" y="380" class="section">Eligibility</text>
  
  <!-- Reports sought -->
  <rect x="150" y="400" width="250" height="70" rx="5" class="box box-elig" />
  <text x="275" y="425" text-anchor="middle" class="label label-bold">Reports sought for retrieval</text>
  <text x="275" y="450" text-anchor="middle" class="number">(n = {s.reports_sought})</text>
  
  <!-- Reports not retrieved -->
  <rect x="500" y="400" width="200" height="70" rx="5" class="box" />
  <text x="600" y="425" text-anchor="middle" class="label label-bold">Reports not retrieved</text>
  <text x="600" y="450" text-anchor="middle" class="number">(n = {s.reports_not_retrieved})</text>
  
  <!-- Arrow -->
  <path d="M 400 435 L 500 435" class="arrow" />
  <path d="M 275 320 L 275 400" class="arrow" />
  
  <!-- Reports assessed -->
  <rect x="150" y="500" width="250" height="70" rx="5" class="box box-elig" />
  <text x="275" y="525" text-anchor="middle" class="label label-bold">Reports assessed for eligibility</text>
  <text x="275" y="550" text-anchor="middle" class="number">(n = {s.reports_assessed})</text>
  
  <!-- Reports excluded with reasons -->
  <rect x="500" y="500" width="350" height="100" rx="5" class="box" />
  <text x="675" y="525" text-anchor="middle" class="label label-bold">Reports excluded (n = {s.reports_excluded})</text>
  {self._format_exclusion_reasons(520, 545)}
  
  <!-- Arrow -->
  <path d="M 400 535 L 500 535" class="arrow" />
  <path d="M 275 470 L 275 500" class="arrow" />
  
  <!-- INCLUDED Section -->
  <text x="30" y="650" class="section">Included</text>
  
  <!-- Studies included -->
  <rect x="150" y="670" width="250" height="90" rx="5" class="box box-inc" />
  <text x="275" y="700" text-anchor="middle" class="label label-bold">Studies included in review</text>
  <text x="275" y="725" text-anchor="middle" class="number">(n = {s.studies_included})</text>
  <text x="275" y="745" text-anchor="middle" class="label">Reports: {s.reports_included}</text>
  
  <!-- Arrow -->
  <path d="M 275 570 L 275 670" class="arrow" />
  
  <!-- Footer -->
  <text x="{width//2}" y="{height - 10}" text-anchor="middle" class="label" style="font-size: 10px; fill: #757575;">
    Generated by ScholaRAG_Graph | PRISMA 2020 Statement (Page MJ, et al. BMJ 2021;372:n71)
  </text>
</svg>'''
        
        return svg
    
    def _format_sources(self) -> str:
        """Format database sources for display (sanitized for SVG)."""
        if not self.stats.database_sources:
            return ""

        # Sanitize source names to prevent XSS
        sources = [f"{_sanitize(name)}: {count}" for name, count in self.stats.database_sources.items()]
        return ", ".join(sources[:3])  # Limit to 3 sources
    
    def _format_exclusion_reasons(self, x: int, start_y: int) -> str:
        """Format exclusion reasons as SVG text elements (sanitized)."""
        if not self.stats.exclusion_reasons:
            return ""

        lines = []
        y = start_y
        for reason, count in list(self.stats.exclusion_reasons.items())[:5]:
            # Sanitize reason text to prevent XSS
            safe_reason = _sanitize(reason)
            lines.append(f'<text x="{x}" y="{y}" class="label">* {safe_reason} (n={count})</text>')
            y += 15

        return "\n  ".join(lines)
    
    def _generate_html(self) -> str:
        """Generate HTML format with embedded SVG (sanitized)."""
        svg = self._generate_svg()
        safe_title = _sanitize(self.title)

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{safe_title}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 950px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .download-btn {{
            display: inline-block;
            padding: 10px 20px;
            background-color: #5C6BC0;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .download-btn:hover {{
            background-color: #3949AB;
        }}
    </style>
</head>
<body>
    <div class="container">
        <a href="#" class="download-btn" onclick="downloadSVG()">Download SVG</a>
        <div id="diagram">
            {svg}
        </div>
    </div>
    <script>
        function downloadSVG() {{
            const svg = document.querySelector('#diagram svg');
            const svgData = new XMLSerializer().serializeToString(svg);
            const blob = new Blob([svgData], {{type: 'image/svg+xml'}});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'prisma_diagram.svg';
            a.click();
            URL.revokeObjectURL(url);
        }}
    </script>
</body>
</html>'''
    
    def _generate_json(self) -> str:
        """Generate JSON format statistics."""
        import json
        
        data = {
            "title": self.title,
            "statistics": {
                "identification": {
                    "databases": self.stats.records_identified_databases,
                    "registers": self.stats.records_identified_registers,
                    "other": self.stats.records_identified_other,
                    "sources": self.stats.database_sources,
                    "total": self.stats.total_identified,
                },
                "deduplication": {
                    "removed": self.stats.duplicates_removed,
                    "remaining": self.stats.after_deduplication,
                },
                "screening": {
                    "screened": self.stats.records_screened,
                    "excluded": self.stats.records_excluded_screening,
                },
                "eligibility": {
                    "sought": self.stats.reports_sought,
                    "not_retrieved": self.stats.reports_not_retrieved,
                    "assessed": self.stats.reports_assessed,
                    "excluded": self.stats.reports_excluded,
                    "exclusion_reasons": self.stats.exclusion_reasons,
                },
                "included": {
                    "studies": self.stats.studies_included,
                    "reports": self.stats.reports_included,
                },
            },
            "validation_errors": self.stats.validate(),
        }
        
        return json.dumps(data, indent=2)
    
    def _generate_mermaid(self) -> str:
        """Generate Mermaid.js flowchart format."""
        s = self.stats
        
        return f'''flowchart TD
    subgraph Identification
        A[Records from databases<br/>n = {s.records_identified_databases}]
        B[Records from other sources<br/>n = {s.records_identified_registers + s.records_identified_other}]
        C[Duplicates removed<br/>n = {s.duplicates_removed}]
    end
    
    subgraph Screening
        D[Records screened<br/>n = {s.records_screened}]
        E[Records excluded<br/>n = {s.records_excluded_screening}]
    end
    
    subgraph Eligibility
        F[Reports sought for retrieval<br/>n = {s.reports_sought}]
        G[Reports not retrieved<br/>n = {s.reports_not_retrieved}]
        H[Reports assessed for eligibility<br/>n = {s.reports_assessed}]
        I[Reports excluded<br/>n = {s.reports_excluded}]
    end
    
    subgraph Included
        J[Studies included in review<br/>n = {s.studies_included}<br/>Reports: {s.reports_included}]
    end
    
    A --> C
    B --> C
    C --> D
    D --> E
    D --> F
    F --> G
    F --> H
    H --> I
    H --> J'''


async def generate_prisma_from_project(project_id: str, db) -> PRISMAStatistics:
    """
    Generate PRISMA statistics from a ScholaRAG_Graph project.
    
    Args:
        project_id: Project ID
        db: Database connection
        
    Returns:
        PRISMAStatistics populated from project data
    """
    # Get project metadata
    project = await db.fetchrow(
        "SELECT * FROM projects WHERE id = $1",
        project_id
    )
    
    if not project:
        raise ValueError(f"Project not found: {project_id}")
    
    # Get paper counts by status (assuming status tracking)
    # These queries would need to be adapted to actual schema
    
    stats = PRISMAStatistics()
    
    # Get total papers identified
    total = await db.fetchval(
        "SELECT COUNT(*) FROM papers WHERE project_id = $1",
        project_id
    )
    stats.records_identified_databases = total or 0
    
    # Get duplicates removed
    # Assuming we track this or can calculate from metadata
    duplicates = await db.fetchval(
        """
        SELECT COUNT(*) FROM papers p1
        WHERE project_id = $1
        AND EXISTS (
            SELECT 1 FROM papers p2 
            WHERE p2.project_id = p1.project_id 
            AND p2.id < p1.id 
            AND (p2.doi = p1.doi OR p2.title = p1.title)
        )
        """,
        project_id
    )
    stats.duplicates_removed = duplicates or 0
    
    # Get screened papers
    screened = await db.fetchval(
        "SELECT COUNT(*) FROM papers WHERE project_id = $1 AND screened = true",
        project_id
    )
    stats.records_screened = stats.records_identified_databases - stats.duplicates_removed
    
    # Get excluded at screening
    excluded_screening = await db.fetchval(
        "SELECT COUNT(*) FROM papers WHERE project_id = $1 AND screened = true AND included = false",
        project_id
    )
    stats.records_excluded_screening = excluded_screening or 0
    
    # Get papers for full-text assessment
    stats.reports_sought = stats.records_screened - stats.records_excluded_screening
    
    # Get papers with PDFs
    with_pdf = await db.fetchval(
        "SELECT COUNT(*) FROM papers WHERE project_id = $1 AND pdf_path IS NOT NULL",
        project_id
    )
    stats.reports_not_retrieved = stats.reports_sought - (with_pdf or 0)
    stats.reports_assessed = with_pdf or 0
    
    # Get included papers
    included = await db.fetchval(
        "SELECT COUNT(*) FROM papers WHERE project_id = $1 AND included = true",
        project_id
    )
    stats.studies_included = included or 0
    stats.reports_included = included or 0
    stats.reports_excluded = stats.reports_assessed - stats.studies_included
    
    return stats
