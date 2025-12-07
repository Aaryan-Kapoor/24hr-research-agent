"""
Report Compiler Module for Deep Research Agent
Handles final report generation in multiple formats
"""
import os
import re
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any

from jinja2 import Template, Environment

from .config import get_config, ResearchTask, Source, GlossaryTerm
from .database import get_database
from .tools import read_file, ensure_directory, count_words
from .logger import get_logger, print_success, print_info

logger = get_logger(__name__)


# =============================================================================
# HTML TEMPLATE
# =============================================================================

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        :root {
            --primary: #000000;
            --secondary: #444444;
            --background: #ffffff;
            --surface: #f5f5f5;
            --text: #111111;
            --text-secondary: #555555;
            --border: #dddddd;
            --code-bg: #f0f0f0;
            --accent: #333333;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Georgia', 'Times New Roman', serif;
            line-height: 1.8;
            color: var(--text);
            background: var(--background);
            max-width: 800px;
            margin: 0 auto;
            padding: 3rem 2rem;
        }
        
        header {
            text-align: center;
            margin-bottom: 3rem;
            padding-bottom: 2rem;
            border-bottom: 2px solid var(--primary);
        }
        
        h1 {
            font-size: 2.2rem;
            margin-bottom: 0.75rem;
            color: var(--primary);
            font-weight: 700;
            letter-spacing: -0.5px;
        }
        
        .subtitle {
            color: var(--text-secondary);
            font-size: 1.1rem;
            font-style: italic;
        }
        
        .meta {
            margin-top: 1.5rem;
            font-size: 0.9rem;
            color: var(--secondary);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        
        h2 {
            font-size: 1.6rem;
            margin-top: 3rem;
            margin-bottom: 1rem;
            color: var(--primary);
            padding-bottom: 0.5rem;
            border-bottom: 1px solid var(--border);
            font-weight: 600;
        }
        
        h3 {
            font-size: 1.3rem;
            margin-top: 2rem;
            margin-bottom: 0.75rem;
            color: var(--text);
            font-weight: 600;
        }
        
        h4 {
            font-size: 1.1rem;
            margin-top: 1.5rem;
            margin-bottom: 0.5rem;
            font-weight: 600;
        }
        
        p {
            margin-bottom: 1.2rem;
            text-align: justify;
        }
        
        a {
            color: var(--accent);
            text-decoration: underline;
        }
        
        a:hover {
            color: var(--primary);
        }
        
        blockquote {
            border-left: 3px solid var(--primary);
            padding-left: 1.5rem;
            margin: 1.5rem 0;
            color: var(--text-secondary);
            font-style: italic;
        }
        
        code {
            background: var(--code-bg);
            padding: 0.2rem 0.4rem;
            border-radius: 3px;
            font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
            font-size: 0.85em;
            border: 1px solid var(--border);
        }
        
        pre {
            background: var(--code-bg);
            padding: 1rem;
            border-radius: 4px;
            overflow-x: auto;
            margin: 1.5rem 0;
            border: 1px solid var(--border);
        }
        
        pre code {
            background: none;
            padding: 0;
            border: none;
        }
        
        ul, ol {
            margin: 1rem 0;
            padding-left: 2rem;
        }
        
        li {
            margin-bottom: 0.5rem;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 1.5rem 0;
        }
        
        th, td {
            border: 1px solid var(--border);
            padding: 0.75rem;
            text-align: left;
        }
        
        th {
            background: var(--surface);
            font-weight: 600;
        }
        
        .toc {
            background: var(--surface);
            padding: 1.5rem 2rem;
            border: 1px solid var(--border);
            margin-bottom: 2rem;
        }
        
        .toc h2 {
            margin-top: 0;
            border: none;
            padding: 0;
            font-size: 1.2rem;
        }
        
        .toc ul {
            list-style: none;
            padding-left: 0;
            margin-bottom: 0;
        }
        
        .toc li {
            padding: 0.3rem 0;
            border-bottom: 1px dotted var(--border);
        }
        
        .toc li:last-child {
            border-bottom: none;
        }
        
        .toc a {
            color: var(--text);
            text-decoration: none;
        }
        
        .toc a:hover {
            text-decoration: underline;
        }
        
        .bibliography {
            background: var(--surface);
            padding: 1.5rem 2rem;
            border: 1px solid var(--border);
            margin-top: 3rem;
        }
        
        .bibliography h2 {
            margin-top: 0;
            font-size: 1.2rem;
        }
        
        .bibliography ol {
            padding-left: 1.5rem;
            margin-bottom: 0;
        }
        
        .bibliography li {
            margin-bottom: 0.75rem;
            word-break: break-word;
            font-size: 0.9rem;
        }
        
        .glossary {
            background: var(--surface);
            padding: 1.5rem 2rem;
            border: 1px solid var(--border);
            margin-top: 2rem;
        }
        
        .glossary h2 {
            margin-top: 0;
            font-size: 1.2rem;
        }
        
        .glossary dt {
            font-weight: 600;
            margin-top: 1rem;
        }
        
        .glossary dt:first-of-type {
            margin-top: 0.5rem;
        }
        
        .glossary dd {
            margin-left: 1rem;
            color: var(--text-secondary);
        }
        
        .citation {
            color: var(--secondary);
            font-size: 0.85em;
        }
        
        hr {
            border: none;
            border-top: 1px solid var(--border);
            margin: 2rem 0;
        }
        
        footer {
            margin-top: 3rem;
            padding-top: 2rem;
            border-top: 2px solid var(--primary);
            text-align: center;
            color: var(--text-secondary);
            font-size: 0.85rem;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        
        @media print {
            body {
                max-width: none;
                padding: 1rem;
                font-size: 11pt;
            }
            
            h2 {
                page-break-before: always;
            }
            
            h2:first-of-type {
                page-break-before: avoid;
            }
            
            .toc, .bibliography, .glossary {
                background: none;
                border: 1px solid #000;
            }
        }
    </style>
</head>
<body>
    <header>
        <h1>{{ title }}</h1>
        {% if subtitle %}
        <p class="subtitle">{{ subtitle }}</p>
        {% endif %}
        <p class="meta">
            Generated on {{ generated_date }}<br>
            {{ word_count | format_number }} words | {{ source_count }} sources | {{ section_count }} sections
        </p>
    </header>
    
    {% if toc %}
    <nav class="toc">
        <h2>Table of Contents</h2>
        <ul>
        {% for item in toc %}
            <li><a href="#{{ item.id }}">{{ item.title }}</a></li>
        {% endfor %}
        </ul>
    </nav>
    {% endif %}
    
    <main>
    {{ content }}
    </main>
    
    {% if glossary %}
    <section class="glossary">
        <h2>Glossary</h2>
        <dl>
        {% for term in glossary %}
            <dt>{{ term.term }}</dt>
            <dd>{{ term.definition }}</dd>
        {% endfor %}
        </dl>
    </section>
    {% endif %}
    
    {% if bibliography %}
    <section class="bibliography">
        <h2>Bibliography</h2>
        <ol>
        {% for source in bibliography %}
            <li>
                <strong>{{ source.title }}</strong><br>
                <a href="{{ source.url }}" target="_blank">{{ source.url }}</a>
                {% if source.is_academic %}<span class="citation">[Academic]</span>{% endif %}
            </li>
        {% endfor %}
        </ol>
    </section>
    {% endif %}
    
    <footer>
        <p>Generated by Deep Research Agent</p>
        <p>Research completed in {{ duration }}</p>
    </footer>
</body>
</html>
"""


# =============================================================================
# REPORT COMPILER
# =============================================================================

class ReportCompiler:
    """Compiles research into final report formats"""
    
    def __init__(self):
        self.config = get_config()
        self.db = get_database()
    
    def compile_report(
        self,
        query: str,
        executive_summary: str = None,
        conclusion: str = None,
        duration_seconds: float = 0
    ) -> Dict[str, str]:
        """
        Compile all research into final report formats
        Returns dict of format -> file path
        """
        logger.info("Compiling final report...")
        
        # Gather all content
        tasks = self.db.get_all_tasks()
        completed_tasks = [t for t in tasks if t.status == "completed"]
        sources = self.db.get_all_sources()
        glossary_terms = self.db.get_all_glossary_terms()
        
        # Read all chapter files
        chapters = []
        for task in completed_tasks:
            content = read_file(task.file_path)
            if content:
                chapters.append({
                    "task": task,
                    "content": content
                })
        
        # Sort by file path (which includes order number)
        chapters.sort(key=lambda x: x["task"].file_path)
        
        # Calculate statistics
        total_words = sum(count_words(c["content"]) for c in chapters)
        
        # Generate outputs
        output_files = {}
        output_dir = ensure_directory(self.config.output.directory)
        report_name = self.config.output.report_name
        
        for fmt in self.config.output.formats:
            if fmt == "markdown":
                path = self._compile_markdown(
                    output_dir / f"{report_name}.md",
                    query,
                    chapters,
                    sources,
                    glossary_terms,
                    executive_summary,
                    conclusion,
                    total_words
                )
                output_files["markdown"] = str(path)
                
            elif fmt == "html":
                path = self._compile_html(
                    output_dir / f"{report_name}.html",
                    query,
                    chapters,
                    sources,
                    glossary_terms,
                    executive_summary,
                    conclusion,
                    total_words,
                    duration_seconds
                )
                output_files["html"] = str(path)
                
            elif fmt == "pdf":
                # PDF requires HTML first
                html_path = self._compile_html(
                    output_dir / f"{report_name}_temp.html",
                    query,
                    chapters,
                    sources,
                    glossary_terms,
                    executive_summary,
                    conclusion,
                    total_words,
                    duration_seconds
                )
                pdf_path = self._html_to_pdf(
                    html_path,
                    output_dir / f"{report_name}.pdf"
                )
                if pdf_path:
                    output_files["pdf"] = str(pdf_path)
                    # Clean up temp HTML
                    os.remove(html_path)
        
        print_success(f"Report compiled: {', '.join(output_files.keys())}")
        return output_files
    
    def _compile_markdown(
        self,
        output_path: Path,
        query: str,
        chapters: List[Dict],
        sources: List[Source],
        glossary_terms: List[GlossaryTerm],
        executive_summary: str,
        conclusion: str,
        total_words: int
    ) -> Path:
        """Compile to Markdown format"""
        lines = []
        
        # Title
        lines.append(f"# Deep Research Report")
        lines.append("")
        lines.append(f"**Query:** {query}")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"**Words:** {total_words:,}")
        lines.append(f"**Sources:** {len(sources)}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Table of Contents
        if self.config.output.include_toc:
            lines.append("## Table of Contents")
            lines.append("")
            for i, chapter in enumerate(chapters, 1):
                title = chapter["task"].topic
                anchor = self._slugify(title)
                lines.append(f"{i}. [{title}](#{anchor})")
            lines.append("")
            lines.append("---")
            lines.append("")
        
        # Executive Summary
        if executive_summary and self.config.output.include_summary:
            lines.append("## Executive Summary")
            lines.append("")
            lines.append(executive_summary)
            lines.append("")
            lines.append("---")
            lines.append("")
        
        # Main Content
        for chapter in chapters:
            content = chapter["content"]
            # Ensure proper heading levels
            content = self._normalize_headings(content)
            lines.append(content)
            lines.append("")
            lines.append("---")
            lines.append("")
        
        # Conclusion
        if conclusion:
            lines.append("## Conclusion")
            lines.append("")
            lines.append(conclusion)
            lines.append("")
            lines.append("---")
            lines.append("")
        
        # Glossary
        if glossary_terms and self.config.output.include_glossary:
            lines.append("## Glossary")
            lines.append("")
            for term in sorted(glossary_terms, key=lambda t: t.term.lower()):
                lines.append(f"**{term.term}**: {term.definition}")
                lines.append("")
            lines.append("---")
            lines.append("")
        
        # Bibliography
        if sources and self.config.output.include_bibliography:
            lines.append("## Bibliography")
            lines.append("")
            for i, source in enumerate(sources, 1):
                academic = " [Academic]" if source.is_academic else ""
                lines.append(f"{i}. **{source.title}**{academic}")
                lines.append(f"   {source.url}")
                lines.append("")
        
        # Write file
        content = "\n".join(lines)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print_info(f"Markdown: {output_path}")
        return output_path
    
    def _compile_html(
        self,
        output_path: Path,
        query: str,
        chapters: List[Dict],
        sources: List[Source],
        glossary_terms: List[GlossaryTerm],
        executive_summary: str,
        conclusion: str,
        total_words: int,
        duration_seconds: float
    ) -> Path:
        """Compile to HTML format"""
        import markdown
        
        # Build TOC
        toc = []
        if self.config.output.include_toc:
            for chapter in chapters:
                title = chapter["task"].topic
                toc.append({
                    "id": self._slugify(title),
                    "title": title
                })
        
        # Convert content to HTML
        content_parts = []
        
        # Executive Summary
        if executive_summary and self.config.output.include_summary:
            content_parts.append(f'<h2 id="executive-summary">Executive Summary</h2>')
            content_parts.append(markdown.markdown(executive_summary))
        
        # Main chapters
        for chapter in chapters:
            task = chapter["task"]
            md_content = chapter["content"]
            
            # Add anchor for TOC
            anchor = self._slugify(task.topic)
            content_parts.append(f'<section id="{anchor}">')
            
            # Convert markdown to HTML
            html_content = markdown.markdown(
                md_content,
                extensions=['tables', 'fenced_code', 'toc']
            )
            content_parts.append(html_content)
            content_parts.append('</section>')
            content_parts.append('<hr>')
        
        # Conclusion
        if conclusion:
            content_parts.append('<h2 id="conclusion">Conclusion</h2>')
            content_parts.append(markdown.markdown(conclusion))
        
        # Format duration
        if duration_seconds > 3600:
            duration = f"{duration_seconds/3600:.1f} hours"
        elif duration_seconds > 60:
            duration = f"{duration_seconds/60:.1f} minutes"
        else:
            duration = f"{duration_seconds:.0f} seconds"
        
        # Create Jinja environment with custom filters
        env = Environment()
        env.filters['format_number'] = lambda x: f"{x:,}"
        template = env.from_string(HTML_TEMPLATE)
        
        # Prepare bibliography for template
        bibliography = []
        if sources and self.config.output.include_bibliography:
            for source in sources:
                bibliography.append({
                    "title": source.title,
                    "url": source.url,
                    "is_academic": source.is_academic
                })
        
        # Prepare glossary for template
        glossary = []
        if glossary_terms and self.config.output.include_glossary:
            for term in sorted(glossary_terms, key=lambda t: t.term.lower()):
                glossary.append({
                    "term": term.term,
                    "definition": term.definition
                })
        
        # Render HTML
        html = template.render(
            title="Deep Research Report",
            subtitle=query[:200],
            generated_date=datetime.now().strftime('%B %d, %Y at %H:%M'),
            word_count=total_words,
            source_count=len(sources),
            section_count=len(chapters),
            toc=toc if self.config.output.include_toc else None,
            content="\n".join(content_parts),
            glossary=glossary if glossary else None,
            bibliography=bibliography if bibliography else None,
            duration=duration
        )
        
        # Write file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print_info(f"HTML: {output_path}")
        return output_path
    
    def _html_to_pdf(self, html_path: Path, pdf_path: Path) -> Optional[Path]:
        """Convert HTML to PDF using WeasyPrint"""
        try:
            from weasyprint import HTML
            HTML(filename=str(html_path)).write_pdf(str(pdf_path))
            print_info(f"PDF: {pdf_path}")
            return pdf_path
        except ImportError:
            logger.warning("WeasyPrint not installed. Skipping PDF generation.")
            return None
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            return None
    
    def _slugify(self, text: str) -> str:
        """Convert text to URL-friendly slug"""
        text = text.lower()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[\s_]+', '-', text)
        text = re.sub(r'-+', '-', text)
        return text.strip('-')
    
    def _normalize_headings(self, content: str) -> str:
        """Ensure headings are properly formatted"""
        # Make sure # headings have space after #
        content = re.sub(r'^(#{1,6})([^\s#])', r'\1 \2', content, flags=re.MULTILINE)
        return content