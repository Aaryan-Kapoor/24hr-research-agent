# 24 Hour Deep Research Agent

An experimental 24-hour automated research system that produces comprehensive, book-length reports with citations on any topic.

## Features

- **Comprehensive Research**: Automatically breaks down complex topics into hundreds of sub-questions
- **24-Hour Capability**: Designed for long-running research sessions with state persistence
- **Multi-Source Search**: Integrates with Tavily, Serper, and Brave search APIs
- **Intelligent Scraping**: Extracts and processes content from web pages
- **Citation Management**: Automatically tracks and cites all sources
- **Recursive Discovery**: Automatically discovers and researches related sub-topics
- **Quality Control**: Validates sources and content quality
- **Multiple Export Formats**: Markdown, HTML, and PDF output
- **Progress Persistence**: Resume interrupted sessions at any time
- **Rate Limiting**: Built-in rate limiting to respect API limits
- **Beautiful CLI**: Rich terminal output with progress tracking

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Planner Agent  │────▶│ Researcher Agent│────▶│  Editor Agent   │
│  (Creates Plan) │     │  (Deep Dives)   │     │ (Compiles)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     State Database (SQLite)                      │
│  • Tasks • Sources • Glossary • Sessions                        │
└─────────────────────────────────────────────────────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   LLM Client    │     │   Web Search    │     │   Web Scraper   │
│ (Claude/GPT/OR) │     │ (Tavily/Serper) │     │ (Tavily/BSoup4) │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Quick Start

### 1. Installation

```bash
# Clone or download the project
cd deep-research-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env  # or use your preferred editor

# Copy config template (optional)
cp config.example.yaml config.yaml
```

**Required API Keys:**
- **LLM Provider** (one of):
  - `ANTHROPIC_API_KEY` - [Get key](https://console.anthropic.com/)
  - `OPENAI_API_KEY` - [Get key](https://platform.openai.com/api-keys)
  - `OPENROUTER_API_KEY` - [Get key](https://openrouter.ai/keys)

- **Search Provider** (one of):
  - `TAVILY_API_KEY` (Recommended) - [Get key](https://tavily.com/)
  - `SERPER_API_KEY` - [Get key](https://serper.dev/)
  - `BRAVE_API_KEY` - [Get key](https://brave.com/search/api/)

### 3. Run Research

```bash
# Interactive mode
python main.py research

# With query argument
python main.py research "A comprehensive analysis of quantum computing hardware"

# Resume interrupted session
python main.py research --resume
```

## CLI Commands

```bash
# Start new research
python main.py research "Your research query"

# Resume existing session
python main.py research --resume

# Check session status
python main.py status

# Export to different formats
python main.py export --format html
python main.py export --format markdown
python main.py export --format all

# Reset database (clear all progress)
python main.py reset

# Validate configuration
python main.py validate

# Show help
python main.py --help
```

## Configuration

Edit `config.yaml` to customize:

```yaml
# LLM Settings
llm:
  provider: "anthropic"  # anthropic, openai, openrouter
  models:
    planner: "claude-sonnet-4-20250514"
    researcher: "claude-sonnet-4-20250514"
    writer: "claude-sonnet-4-20250514"

# Search Settings
search:
  provider: "tavily"  # tavily, serper, brave
  max_results: 8
  queries_per_task: 3

# Research Parameters
research:
  min_initial_tasks: 10
  max_total_tasks: 200
  max_recursion_depth: 3
  min_words_per_section: 500
  max_runtime_hours: 24

# Output Settings
output:
  formats: ["markdown", "html"]
  include_toc: true
  include_bibliography: true
```

## Project Structure

```
deep-research-agent/
├── main.py              # Entry point
├── cli.py               # CLI interface
├── config.yaml          # Configuration file
├── config.example.yaml  # Configuration template
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (create from .env.example)
├── .env.example         # Environment template
├── src/
│   ├── __init__.py     # Package init
│   ├── config.py       # Configuration & models
│   ├── database.py     # SQLite state management
│   ├── llm_client.py   # LLM provider abstraction
│   ├── agents.py       # Planner, Researcher, Editor agents
│   ├── tools.py        # Search & scraping tools
│   ├── compiler.py     # Report compilation
│   ├── orchestrator.py # Main research loop
│   └── logger.py       # Logging & rich output
├── report/             # Generated report chapters
├── logs/               # Log files
└── research_state.db   # SQLite database (created at runtime)
```

## How It Works

### Phase 1: Planning
The **Planner Agent** analyzes your query and creates a comprehensive research plan with 10-200+ tasks, structured like a book outline.

### Phase 2: Research Loop
The **Researcher Agent** iteratively:
1. Picks the next pending task
2. Generates targeted search queries
3. Searches and scrapes relevant sources
4. Synthesizes findings into detailed markdown
5. Discovers and adds new sub-topics (recursive research)
6. Updates progress in the database

### Phase 3: Compilation
The **Editor Agent** and **Compiler**:
1. Generate an executive summary
2. Create a conclusion
3. Compile all chapters into final reports
4. Generate table of contents, bibliography, and glossary

## Resilience Features

- **State Persistence**: All progress saved to SQLite database
- **Graceful Shutdown**: Ctrl+C saves progress and compiles partial report
- **Resume Capability**: Continue from where you left off
- **Error Recovery**: Failed tasks are logged and skipped
- **Rate Limiting**: Prevents API throttling
- **Retry Logic**: Automatic retries with exponential backoff

## Example Output

After a research session, you'll have:

```
report/
├── 01_Introduction.md
├── 02_Historical_Background.md
├── 03_Core_Concepts.md
├── 04_Technical_Analysis.md
├── ...
├── DEEP_RESEARCH_REPORT.md    # Combined markdown
├── DEEP_RESEARCH_REPORT.html  # Styled HTML report
└── DEEP_RESEARCH_REPORT.pdf   # PDF (if weasyprint installed)
```

## Extending

### Adding New LLM Providers

1. Create a new client class in `src/llm_client.py` inheriting from `BaseLLMClient`
2. Implement `complete()` and `complete_with_messages()` methods
3. Add provider to the factory function

### Adding New Search Providers

1. Add search function in `src/tools.py`
2. Add provider enum in `src/config.py`
3. Update `web_search()` function to handle new provider

## Troubleshooting

**"API key not set"**
- Ensure your `.env` file exists and contains the required keys
- Check that the provider in `config.yaml` matches your available API key

**"Rate limit exceeded"**
- Reduce `rate_limits` values in `config.yaml`
- Add delays between sessions in `research.session_delay`

**"No tasks found"**
- Check `research_state.db` exists
- Try `python main.py reset` and start fresh

**"PDF generation failed"**
- Install WeasyPrint: `pip install weasyprint`
- WeasyPrint may require system dependencies on some platforms

## License

MIT License - Use freely for personal and commercial projects.

## Contributing

Contributions welcome! Please open an issue or PR.

---

Built with ❤️ for comprehensive research automation.
