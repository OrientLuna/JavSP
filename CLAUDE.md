# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

JavSP is a Chinese AV metadata scraper that aggregates data from multiple websites to generate NFO files for media servers like Emby, Jellyfin, and Kodi. The project automatically identifies movie IDs from filenames, scrapes data from multiple sources, and organizes files according to configurable naming rules.

## Development Commands

### Installation and Dependencies
```bash
# Install dependencies using Poetry
poetry install

# Install development dependencies
poetry install --with dev

# Activate the virtual environment
poetry shell
```

### Running the Application
```bash
# Run the main application
python -m javsp

# Or using Poetry script
poetry run javsp

# Display help and command line options
python -m javsp -h
```

### Testing
```bash
# Run tests (if present)
poetry run pytest

# Run specific test modules
poetry run pytest tests/test_module.py

# Run tests with coverage
poetry run pytest --cov=javsp
```

### Code Quality
```bash
# Run linting
poetry run flake8 javsp/

# Type checking (if mypy is added)
poetry run mypy javsp/
```

### Building and Packaging
```bash
# Build executable using cx_Freeze
python setup.py build

# Create distributable package
poetry build
```

## Configuration

The application uses `config.yml` as its main configuration file. Key configuration sections:

- **scanner**: File scanning and movie ID detection settings
- **network**: Proxy, retry, and timeout configurations
- **crawler**: Which websites to scrape and in what order
- **summarizer**: File organization and naming rules
- **translator**: Translation engine settings (Google, Bing, Baidu, etc.)

## Architecture

### Core Components

1. **Main Entry Point** (`javsp/__main__.py`)
   - Handles workflow orchestration
   - Manages parallel crawling with threading
   - Coordinates data summarization and file operations

2. **Data Models** (`javsp/datatype.py`)
   - `Movie`: Represents a movie with files and metadata
   - `MovieInfo`: Contains scraped movie information
   - Manages data persistence and template generation

3. **Configuration System** (`javsp/config.py`)
   - Uses Pydantic for configuration validation
   - Supports multiple sources: file, environment, command line
   - Type-safe configuration with proper validation

4. **Web Crawlers** (`javsp/web/`)
   - Each crawler in separate module (e.g., `javdb.py`, `avsox.py`)
   - Base functionality in `javsp/web/base.py`
   - Handles site-specific parsing and network requests
   - Exception handling for various failure modes

5. **File Operations** (`javsp/file.py`)
   - Movie ID detection from filenames
   - File scanning and organization
   - Path generation based on templates

6. **Image Processing** (`javsp/image.py`, `javsp/cropper/`)
   - Cover image downloading and processing
   - AI-based cropping for non-standard posters
   - Support for multiple cropping engines

### Data Flow

1. **Scanning Phase**:
   - Scan directory for video files
   - Extract movie IDs from filenames
   - Optional manual review mode

2. **Crawling Phase**:
   - Parallel execution of configured crawlers
   - Each crawler populates a `MovieInfo` object
   - Automatic retry and error handling

3. **Summarization Phase**:
   - Merge data from multiple sources by priority
   - Handle special cases (actress name normalization, genre consolidation)
   - Validate required fields are present

4. **Processing Phase**:
   - Download and process cover images
   - Generate file paths using templates
   - Create NFO files for media servers
   - Move/rename files to final locations

### Crawler Architecture

Each crawler follows a consistent pattern:
- Export `parse_data(info: MovieInfo)` function
- Use `Request` class for network operations
- Populate `MovieInfo` attributes directly
- Handle site-specific exceptions from `javsp/web/exceptions.py`

### Threading Model

The application uses multithreading for parallel crawling:
- Each crawler runs in separate thread
- Configurable retry count and timeout
- Thread-safe data aggregation
- Progress tracking with tqdm integration

## Testing and Development Tools

### Utility Scripts (in `tools/`)
- `config_migration.py`: Migrate old config.ini to config.yml
- `call_crawler.py`: Test individual crawlers
- `check_genre.py`: Validate genre translations
- `airav_search.py`: Search functionality testing

### Data Files
- `data/actress_alias.json`: Actress name normalization mapping
- `data/` directory contains genre mappings and other reference data

## Adding New Crawlers

1. Create new module in `javsp/web/`
2. Implement `parse_data(info: MovieInfo)` function
3. Add crawler ID to `CrawlerID` enum in `config.py`
4. Import module in `import_crawlers()` function
5. Add to appropriate crawler list in `config.yml`

## Key Design Patterns

- **Configuration-driven**: Behavior controlled through `config.yml`
- **Plugin architecture**: Crawlers are modular and swappable
- **Parallel processing**: Multi-threaded scraping for performance
- **Graceful degradation**: Continues when some sources fail
- **Template-based naming**: Flexible file organization patterns

## Important Notes

- This is a Chinese-language project with Chinese UI and logging
- Web scraping handles CloudFlare protection via cloudscraper
- Supports both regular DVD IDs and DMM Content IDs
- Includes AI-based image cropping for non-standard covers
- Translation support for titles and plots via multiple engines