# IMAP Message Filter

A Python-based mail filtering utility that connects to remote mail servers using the Internet Message Access Protocol (IMAP) to automatically organize emails based on configurable rules.

## Overview

IMAPMessageFilter is designed to run as a command-line utility that can be scheduled to run on system startup or as a scheduled job. It provides secure, automated email organization by moving messages from the Inbox to appropriate folders based on user-defined filtering rules.

## Use Case

Thunderbird desktop users can configure and run message filters but Thunderbird mobile users cannot. This application can periodically run, on a home or cloud server, and execute the configured message filters. 
The existing Thunderbird config, including message filters, can be used in setup phase to reduce manual updates.

## Requirements

### Functional Requirements

#### Core Functionality
- **IMAP Connection Management**
  - Connect to remote mail servers using IMAP protocol
  - Support for IMAP over SSL/TLS (IMAPS) for enhanced security
  - Handle connection authentication with username/password or OAuth2
  - Implement connection pooling and retry mechanisms
  - Graceful handling of network timeouts and connection failures

#### Message Filtering
- **Filter Rule Engine**
  - Support multiple filter criteria:
    - Sender email address/domain
    - Subject line content (exact match, contains, regex)
    - Message body content (keyword search, regex)
    - Message size
    - Date received
    - Header fields (To, CC, BCC, etc.)
    - Attachment presence/type
  - Boolean logic support (AND, OR, NOT combinations)
  - Priority-based rule ordering
  - Case-sensitive and case-insensitive matching options

#### Folder Management
- **Target Folder Operations**
  - Create destination folders if they don't exist
  - Support nested folder structures
  - Handle folder naming conflicts
  - Maintain folder hierarchy across sessions

#### Message Operations
- **Email Processing**
  - Move messages from Inbox to target folders
  - Copy messages (optional)
  - Mark messages as read/unread
  - Add/remove message flags
  - Delete messages (optional)
  - Preserve message metadata and attachments

### Technical Requirements

#### Security
- **Authentication & Encryption**
  - Support for IMAPS (IMAP over SSL/TLS)
  - OAuth2 authentication support
  - Secure credential storage (environment variables, config files)
  - Certificate validation for SSL connections
  - No hardcoded credentials in source code

#### Configuration Management
- **Configuration System**
  - YAML/JSON configuration files
  - Environment variable support for sensitive data
  - Multiple server configurations
  - Filter rule definitions
  - Logging configuration
  - Error handling preferences

#### Logging & Monitoring
- **Observability**
  - Comprehensive logging (INFO, WARNING, ERROR, DEBUG levels)
  - Structured logging with timestamps
  - Log rotation and size management
  - Performance metrics collection
  - Error reporting and alerting capabilities

#### Performance
- **Efficiency**
  - Batch processing of messages
  - Configurable batch sizes
  - Memory-efficient message handling
  - Timeout handling for long operations
  - Resource cleanup after operations

### Implementation Requirements

#### Python Environment
- **Language & Runtime**
  - Python 3.11+ compatibility
  - Use of modern Python features (type hints, dataclasses, etc.)
  - Async/await support for concurrent operations
  - Proper exception handling and error recovery

#### Dependencies
- **External Libraries**
  - `imaplib` or `imapclient` for IMAP operations
  - `email` for message parsing
  - `yaml` or `json` for configuration
  - `logging` for structured logging
  - `asyncio` for async operations
  - `pydantic` for data validation
  - `click` or `argparse` for CLI interface

#### Command Line Interface
- **CLI Features**
  - Configuration file specification
  - Verbose/debug mode
  - Dry-run mode for testing
  - Single-run vs daemon mode
  - Help and usage information
  - Version information

#### System Integration
- **Deployment**
  - Systemd service file for Linux startup
  - Cron job configuration examples
  - Docker containerization support
  - Configuration file templates
  - Installation scripts

### Non-Functional Requirements

#### Reliability
- **Error Handling**
  - Graceful degradation on partial failures
  - Retry mechanisms with exponential backoff
  - Transaction-like operations for message moves
  - Rollback capabilities for failed operations

#### Scalability
- **Performance**
  - Support for large mailboxes (100k+ messages)
  - Efficient memory usage
  - Configurable processing limits
  - Background processing capabilities

#### Maintainability
- **Code Quality**
  - Comprehensive unit tests
  - Integration tests
  - Code documentation
  - Type hints throughout
  - Modular architecture

#### Usability
- **User Experience**
  - Clear error messages
  - Progress indicators for long operations
  - Configuration validation
  - Example configurations
  - Troubleshooting guide

## Development Phases

### Phase 1: Core IMAP Connectivity ✅
- Basic IMAP connection and authentication
- Simple message listing and retrieval
- Configuration file parsing
- CLI interface with connection testing and message listing
- Comprehensive error handling and logging
- **Thunderbird configuration extraction** - Extract IMAP settings from Thunderbird profiles
- **External configuration management** - Store config in `~/.config/IMAPMessageFilter/`

### Phase 2: Filter Engine & Thunderbird Integration ✅
- **Thunderbird filter extraction** - Extract existing message filters from Thunderbird
- **Filter configuration parsing** - Read and parse `filters.yaml` format
- **Filter rule implementation** - Support for conditions and actions
- **Message matching logic** - Match emails against filter conditions
- **Folder creation and management** - Create target folders as needed
- **Filter validation** - Validate filter rules and syntax

### Phase 3: Message Operations
- Message moving functionality using extracted filter rules
- Error handling and logging for filter operations
- CLI interface for filter management
- **Filter testing** - Test filters against existing messages
- **Dry-run mode** - Preview filter actions without executing

### Phase 4: Advanced Features
- Complex filter rules (AND/OR logic, multiple conditions)
- Performance optimizations for large mailboxes
- **Filter import/export** - Backup and restore filter configurations
- **Filter templates** - Pre-built filter templates for common use cases
- System integration (cron jobs, systemd services)

### Phase 5: Production Readiness
- Comprehensive testing with real filter scenarios
- Documentation and user guides
- Deployment automation
- **Filter monitoring** - Track filter effectiveness and performance
- **Filter analytics** - Statistics on filter usage and results

## Getting Started

### Prerequisites
- Python 3.11 or higher
- Access to IMAP mail server
- Mail server credentials

### Installation
```bash
# Clone the repository
git clone <repository-url>
cd IMAPMessageFilter

# Install dependencies
uv sync

# Install development dependencies (optional)
uv sync --extra dev

# Run the application
uv run python main.py --help
```

### Configuration
The application uses `~/.config/IMAPMessageFilter/` as the default configuration directory:

- `config.yaml` - IMAP server settings, connection configuration, and filter paths
- `filters.yaml` - Message filter rules (extracted from Thunderbird or manually created)

#### Option 1: Extract from Thunderbird (Recommended)
If you use Thunderbird, you can automatically extract your IMAP settings:

```bash
# Extract settings from Thunderbird
uv run python extract_thunderbird_config.py
```

This will:
- **Detect your operating system** (macOS, Linux, Windows)
- Find your Thunderbird profiles automatically
- Extract IMAP server settings
- **Ask you to choose which account to configure**
- Create a configuration template with your selected account details
- Provide next steps for completion

The script is interactive and will guide you through the process step by step.

**Supported platforms**: macOS, Linux, Windows

#### Option 2: Manual Setup
1. Set up the default configuration file:
   ```bash
   uv run python main.py setup-config
   ```

2. Edit the configuration file with your IMAP server settings:
   ```bash
   # Edit the configuration file
   nano ~/.config/IMAPMessageFilter/config.yaml
   ```

   Or use your preferred editor:
   ```bash
   code ~/.config/IMAPMessageFilter/config.yaml
   ```

3. Update the configuration with your actual settings:
   ```yaml
   imap:
     host: "imap.gmail.com"  # Your IMAP server
     port: 993
     username: "your-email@gmail.com"
     password: "your-app-password"
     use_ssl: true
     timeout: 30
   logging:
     level: "INFO"
     format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
     file: null
   filters:
     filters_path: "~/.config/IMAPMessageFilter/filters.yaml"  # Path to your filters file
   ```

#### Common IMAP Server Settings

| Provider | Host | Port | SSL | Notes |
|----------|------|------|-----|-------|
| Gmail | `imap.gmail.com` | 993 | Yes | Requires App Password if 2FA enabled |
| Outlook/Hotmail | `outlook.office365.com` | 993 | Yes | Use Microsoft account password |
| Yahoo | `imap.mail.yahoo.com` | 993 | Yes | Requires App Password |
| iCloud | `imap.mail.me.com` | 993 | Yes | Requires App-Specific Password |
| AOL | `imap.aol.com` | 993 | Yes | Requires App Password |

**Note**: You can also specify a custom configuration file path using the `--config` option with any command.

### Filter Management

#### Extract Filters from Thunderbird
If you have existing message filters in Thunderbird, you can extract them for use with IMAP Message Filter:

```bash
# Extract existing Thunderbird filters
uv run python extract_thunderbird_filters.py
```

This will:
- **Detect your operating system** (macOS, Linux, Windows)
- Find your Thunderbird profiles automatically
- Extract all message filter rules
- Convert them to the application's YAML format
- Save them to `~/.config/IMAPMessageFilter/filters.yaml`

**Supported platforms**: macOS, Linux, Windows

#### Filter Configuration Format
The `filters.yaml` file uses a structured format for defining filter rules:

```yaml
filters:
  - name: "Filter Name"
    enabled: true
    priority: 1
    conditions:
      - field: "from"
        operator: "contains"
        value: "example@domain.com"
      - field: "subject"
        operator: "contains"
        value: "Important"
    actions:
      - type: "move"
        folder: "INBOX/Important"
```

#### Supported Filter Features
- **Conditions**: Match on `from`, `to`, `subject`, `body`, `date`, etc.
- **Operators**: `contains`, `is`, `starts with`, `ends with`, `doesn't contain`
- **Actions**: `move`, `delete`, `mark` (flag messages)
- **Priority**: Control filter execution order
- **Enabled/Disabled**: Toggle individual filters

#### Filter Path Configuration
The `filters_path` setting in `config.yaml` allows you to specify where your `filters.yaml` file is located:

```yaml
filters:
  filters_path: "~/.config/IMAPMessageFilter/filters.yaml"  # Default location
```

You can customize this path to store your filters in a different location:
```yaml
filters:
  filters_path: "/path/to/your/custom/filters.yaml"  # Custom location
```

### Project Structure

```
IMAPMessageFilter/
├── imapmessagefilter/       # Main package
│   ├── __init__.py          # Package initialization
│   ├── config.py            # Configuration management
│   ├── imap_client.py       # IMAP client wrapper
│   ├── cli.py               # Command-line interface
│   └── filter_engine.py     # Filter processing engine (Phase 2)
├── tests/                   # Test suite
│   ├── __init__.py
│   ├── test_config.py       # Configuration tests
│   └── test_filter_engine.py # Filter engine tests (Phase 2)
├── main.py                  # Application entry point
├── pyproject.toml           # Project configuration
├── extract_thunderbird_config.py    # Thunderbird config extraction
├── extract_thunderbird_filters.py   # Thunderbird filter extraction
└── README.md               # This file
```

#### Configuration Files (External)
```
~/.config/IMAPMessageFilter/
├── config.yaml             # IMAP server configuration
└── filters.yaml            # Message filter rules
```

### Usage

#### Phase 1: Core Connectivity

##### Test Connection
Test your IMAP connection and authentication:
```bash
uv run python main.py test-connection
```

##### List Folders
List all available folders on your mail server:
```bash
uv run python main.py list-folders
```

##### List Messages
List messages from a specific folder:
```bash
# List recent messages from INBOX
uv run python main.py list-messages --folder INBOX --limit 10

# List messages from a specific folder
uv run python main.py list-messages --folder "Sent Items" --limit 5
```

##### Verbose Logging
Enable detailed logging for debugging:
```bash
uv run python main.py test-connection --verbose
```

##### Custom Configuration
Use a different configuration file:
```bash
uv run python main.py test-connection --config /path/to/custom/config.yaml
```

#### Phase 2: Filter Management (Coming Soon)

##### Test Filters
Test your filter rules against existing messages:
```bash
uv run python main.py test-filters --dry-run
```

**Options:**
- `--dry-run` - Show what would be done without executing actions
- `--limit N` - Test against only the N most recent messages
- `--filter-name "Filter Name"` - Test only a specific filter

**Examples:**
```bash
# Test all filters against 10 recent messages (dry run)
uv run python main.py test-filters --dry-run --limit 10

# Test only the HDFC filter against all messages (dry run)
uv run python main.py test-filters --dry-run --filter-name "HDFC"

# Test all filters against all messages (dry run)
uv run python main.py test-filters --dry-run
```

##### Apply Filters
Apply filter rules to process messages:
```bash
uv run python main.py apply-filters
```

**Filter Selection Options:**
- `--filter-name "Filter Name"` - Apply only a specific filter (e.g., `--filter-name "HDFC"`)
- Without `--filter-name` - Apply all enabled filters

**Message Processing Options:**
- `--limit N` - Process only the N most recent messages (e.g., `--limit 10`)
- Without `--limit` - Process all messages in the folder

**Examples:**
```bash
# Apply only the HDFC filter to the 5 most recent messages
uv run python main.py apply-filters --filter-name "HDFC" --limit 5

# Apply all filters to the 10 most recent messages
uv run python main.py apply-filters --limit 10

# Apply only the India Tax filter to all messages
uv run python main.py apply-filters --filter-name "India Tax"

# Apply all filters to all messages (full processing)
uv run python main.py apply-filters
```

##### Filter Status
Check the status of your filters:
```bash
uv run python main.py filter-status
```

#### Understanding Filter vs Message Selection

**Filter Selection** (`--filter-name`):
- Controls **which filter rules** to apply
- Examples: `--filter-name "HDFC"`, `--filter-name "India Tax"`
- When omitted: applies all enabled filters

**Message Selection** (`--limit`):
- Controls **how many emails** to process
- Examples: `--limit 5`, `--limit 100`
- When omitted: processes all messages in the folder

**Combined Examples:**
```bash
# Apply only HDFC filter to 5 recent emails
uv run python main.py apply-filters --filter-name "HDFC" --limit 5

# Apply all filters to 10 recent emails  
uv run python main.py apply-filters --limit 10

# Apply only India Tax filter to ALL emails
uv run python main.py apply-filters --filter-name "India Tax"
```

### Development

#### Running Tests
```bash
uv run pytest tests/
```

#### Code Formatting
```bash
uv run black imapmessagefilter/ tests/
uv run isort imapmessagefilter/ tests/
```

#### Type Checking
```bash
uv run mypy imapmessagefilter/
```

#### Linting
```bash
uv run ruff check imapmessagefilter/ tests/
```

## Contributing

Please read the contributing guidelines before submitting pull requests.

## Project Status

### Current Status: Phase 1 Complete ✅ + Filter Extraction ✅

**Phase 1: Core IMAP Connectivity** has been successfully implemented and includes:

- ✅ **IMAP Connection Management**: Secure SSL/TLS connections with authentication
- ✅ **Configuration System**: YAML-based configuration with validation
- ✅ **CLI Interface**: Command-line tools for testing and basic operations
- ✅ **Message Operations**: List folders and messages with metadata
- ✅ **Error Handling**: Comprehensive logging and exception handling
- ✅ **Testing**: Unit tests with pytest
- ✅ **Code Quality**: Type hints, linting, and formatting tools
- ✅ **Thunderbird Integration**: Extract IMAP settings and filter rules from Thunderbird

**Filter Extraction** has been completed and includes:

- ✅ **Thunderbird Filter Extraction**: Extract existing message filters from Thunderbird profiles
- ✅ **Filter Format Conversion**: Convert Thunderbird format to application YAML format
- ✅ **Filter Configuration**: Store filters in `~/.config/IMAPMessageFilter/filters.yaml`
- ✅ **Filter Analysis**: Parse complex filter conditions and actions

### Next Steps: Phase 2 - Filter Engine Implementation

The next phase will implement the filter processing engine with:
- **Filter Rule Engine**: Parse and validate filter rules from `filters.yaml`
- **Message Matching**: Match emails against filter conditions
- **Action Execution**: Execute filter actions (move, delete, mark)
- **Folder Management**: Create target folders as needed
- **Filter Testing**: Test filters against existing messages
- **Dry-Run Mode**: Preview filter actions without executing

## License

[Add license information here]