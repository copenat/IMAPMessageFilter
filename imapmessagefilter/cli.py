"""Command-line interface for IMAP Message Filter."""

import logging
import sys
from pathlib import Path
from typing import Optional

import click

from .config import AppConfig
from .imap_client import IMAPClientWrapper, IMAPConnectionError, IMAPAuthenticationError
from .filter_engine import FilterEngine, MessageData


def setup_logging(config: AppConfig) -> None:
    """Setup logging configuration."""
    import logging.handlers
    
    # Clear any existing handlers
    logging.getLogger().handlers.clear()
    
    # Create formatter
    if config.logging.cron_mode:
        # Cron mode: simple format without colors, with timestamp
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        # Interactive mode: use configured format
        formatter = logging.Formatter(config.logging.format)
    
    # Create console handler (only if not in cron mode or if verbose)
    if not config.logging.cron_mode or config.logging.level == "DEBUG":
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logging.getLogger().addHandler(console_handler)
    
    # Create file handler if specified
    if config.logging.file:
        # Expand ~ to home directory
        log_file = config.logging.file.replace('~', str(Path.home()))
        
        # Create log directory if it doesn't exist
        log_dir = Path(log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        if config.logging.max_size and config.logging.backup_count:
            # Use rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=config.logging.max_size * 1024 * 1024,  # Convert MB to bytes
                backupCount=config.logging.backup_count,
                encoding='utf-8'
            )
        else:
            # Use regular file handler
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
        
        file_handler.setFormatter(formatter)
        logging.getLogger().addHandler(file_handler)
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, config.logging.level))





@click.group()
@click.version_option()
def cli():
    """IMAP Message Filter - A Python-based mail filtering utility."""
    pass


@cli.command()
@click.option(
    '--config', '-c',
    type=click.Path(path_type=Path),
    help='Configuration file path (YAML). Defaults to ~/.config/IMAPMessageFilter/config.yaml'
)
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def test_connection(config: Optional[Path], verbose: bool):
    """Test IMAP connection and authentication."""
    try:
        # Load configuration
        config_path = str(config) if config else None
        app_config = AppConfig.load_config(config_path)
        
        # Setup logging
        if verbose:
            app_config.logging.level = "DEBUG"
        setup_logging(app_config)
        
        logger = logging.getLogger(__name__)
        logger.info("Testing IMAP connection...")
        
        # Test connection
        with IMAPClientWrapper(app_config.imap) as client:
            logger.info("✓ Connection and authentication successful")
            
            # List folders
            folders = client.list_folders()
            logger.info(f"✓ Found {len(folders)} folders")
            
            if folders:
                logger.info("Available folders:")
                for folder in sorted(folders):
                    logger.info(f"  - {folder}")
        
        logger.info("Connection test completed successfully")
        
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except (IMAPConnectionError, IMAPAuthenticationError) as e:
        click.echo(f"Connection failed: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    '--config', '-c',
    type=click.Path(path_type=Path),
    help='Configuration file path (YAML). Defaults to ~/.config/IMAPMessageFilter/config.yaml'
)
@click.option('--folder', '-f', default='INBOX', help='Folder to list messages from')
@click.option('--limit', '-l', type=int, help='Limit number of messages to show')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def list_messages(config: Optional[Path], folder: str, limit: Optional[int], verbose: bool):
    """List messages from a specified folder."""
    try:
        # Load configuration
        config_path = str(config) if config else None
        app_config = AppConfig.load_config(config_path)
        
        # Setup logging
        if verbose:
            app_config.logging.level = "DEBUG"
        setup_logging(app_config)
        
        logger = logging.getLogger(__name__)
        logger.info(f"Listing messages from folder: {folder}")
        
        # Connect and list messages
        with IMAPClientWrapper(app_config.imap) as client:
            # Select folder
            total_messages, recent_messages = client.select_folder(folder)
            
            # Search for messages
            message_ids = client.search_messages("ALL")
            
            if limit:
                message_ids = message_ids[-limit:]  # Get most recent messages
            
            if not message_ids:
                logger.info("No messages found in the folder")
                return
            
            # Fetch message envelopes
            envelopes = client.fetch_message_envelope(message_ids)
            
            # Display messages
            click.echo(f"\nMessages in '{folder}' (showing {len(message_ids)} of {total_messages}):")
            click.echo("-" * 80)
            
            for msg_id in reversed(message_ids):  # Show newest first
                if msg_id in envelopes:
                    envelope = envelopes[msg_id]
                    
                    # Extract subject
                    subject = envelope.subject
                    if subject:
                        subject = subject.decode('utf-8', errors='ignore')
                    else:
                        subject = "(No subject)"
                    
                    # Extract sender
                    sender = envelope.from_
                    if sender and len(sender) > 0:
                        sender_name = sender[0].name
                        sender_email = sender[0].mailbox.decode('utf-8', errors='ignore')
                        if sender_name:
                            sender_name = sender_name.decode('utf-8', errors='ignore')
                            sender_display = f"{sender_name} <{sender_email}>"
                        else:
                            sender_display = sender_email
                    else:
                        sender_display = "(Unknown sender)"
                    
                    # Extract date
                    date = envelope.date
                    date_str = date.strftime("%Y-%m-%d %H:%M") if date else "(No date)"
                    
                    click.echo(f"ID: {msg_id}")
                    click.echo(f"From: {sender_display}")
                    click.echo(f"Subject: {subject}")
                    click.echo(f"Date: {date_str}")
                    click.echo("-" * 80)
        
        logger.info("Message listing completed")
        
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except (IMAPConnectionError, IMAPAuthenticationError) as e:
        click.echo(f"Connection failed: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@cli.command()
def setup_config():
    """Set up the default configuration file."""
    import yaml
    
    default_config_path = AppConfig.get_default_config_path()
    
    if default_config_path.exists():
        click.echo(f"Configuration file already exists at: {default_config_path}")
        click.echo("Please edit it manually or remove it to create a new one.")
        return
    
    # Create the directory if it doesn't exist
    default_config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create default configuration
    default_config = {
        'imap': {
            'host': 'imap.gmail.com',
            'port': 993,
            'username': 'your-email@gmail.com',
            'password': 'your-app-password',
            'use_ssl': True,
            'timeout': 30
        },
        'logging': {
            'level': 'INFO',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'file': None
        },
        'filters': {
            'filters_path': str(AppConfig.get_default_filters_path())
        }
    }
    
    # Write the configuration file
    with open(default_config_path, 'w', encoding='utf-8') as f:
        yaml.dump(default_config, f, default_flow_style=False, indent=2)
    
    click.echo(f"Configuration file created at: {default_config_path}")
    click.echo("Please edit the file with your actual IMAP server settings.")
    click.echo("Make sure to update the username and password fields!")


@cli.command()
@click.option(
    '--config', '-c',
    type=click.Path(path_type=Path),
    help='Configuration file path (YAML). Defaults to ~/.config/IMAPMessageFilter/config.yaml'
)
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def list_folders(config: Optional[Path], verbose: bool):
    """List all available folders."""
    try:
        # Load configuration
        config_path = str(config) if config else None
        app_config = AppConfig.load_config(config_path)
        
        # Setup logging
        if verbose:
            app_config.logging.level = "DEBUG"
        setup_logging(app_config)
        
        logger = logging.getLogger(__name__)
        logger.info("Listing all folders...")
        
        # Connect and list folders
        with IMAPClientWrapper(app_config.imap) as client:
            folders = client.list_folders()
            
            click.echo(f"\nAvailable folders ({len(folders)} total):")
            click.echo("-" * 40)
            
            for folder in sorted(folders):
                click.echo(f"  {folder}")
        
        logger.info("Folder listing completed")
        
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except (IMAPConnectionError, IMAPAuthenticationError) as e:
        click.echo(f"Connection failed: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    '--config', '-c',
    type=click.Path(path_type=Path),
    help='Configuration file path (YAML). Defaults to ~/.config/IMAPMessageFilter/config.yaml'
)
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def filter_status(config: Optional[Path], verbose: bool):
    """Show the status of loaded filters."""
    try:
        # Load configuration
        config_path = str(config) if config else None
        app_config = AppConfig.load_config(config_path)
        
        # Setup logging
        if verbose:
            app_config.logging.level = "DEBUG"
        setup_logging(app_config)
        
        logger = logging.getLogger(__name__)
        logger.info("Checking filter status...")
        
        # Initialize filter engine
        filter_engine = FilterEngine(app_config.filters.filters_path)
        
        # Get filter summary
        summary = filter_engine.get_filter_summary()
        
        click.echo(f"\n📧 Filter Status")
        click.echo(f"Total filters: {summary['total_filters']}")
        click.echo(f"Enabled filters: {summary['enabled_filters']}")
        click.echo(f"Filters file: {app_config.filters.filters_path}")
        click.echo()
        
        if summary['filters']:
            click.echo("📋 Filter Details:")
            click.echo("-" * 60)
            for filter_info in summary['filters']:
                status = "✅ Enabled" if filter_info['enabled'] else "❌ Disabled"
                click.echo(f"• {filter_info['name']} ({status})")
                click.echo(f"  Priority: {filter_info['priority']}")
                click.echo(f"  Conditions: {filter_info['conditions_count']}")
                click.echo(f"  Actions: {filter_info['actions_count']}")
                click.echo()
        else:
            click.echo("No filters found.")
            click.echo("Use 'uv run python extract_thunderbird_filters.py' to extract filters from Thunderbird")
        
        logger.info("Filter status check completed")
        
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    '--config', '-c',
    type=click.Path(path_type=Path),
    help='Configuration file path (YAML). Defaults to ~/.config/IMAPMessageFilter/config.yaml'
)
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing actions')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def test_filters(config: Optional[Path], dry_run: bool, verbose: bool):
    """Test filters against existing messages."""
    try:
        # Load configuration
        config_path = str(config) if config else None
        app_config = AppConfig.load_config(config_path)
        
        # Setup logging
        if verbose:
            app_config.logging.level = "DEBUG"
        setup_logging(app_config)
        
        logger = logging.getLogger(__name__)
        logger.info("Testing filters against existing messages...")
        
        # Initialize filter engine
        filter_engine = FilterEngine(app_config.filters.filters_path)
        
        # Connect to IMAP server
        with IMAPClientWrapper(app_config.imap) as client:
            # Select INBOX
            total_messages, recent_messages = client.select_folder('INBOX')
            
            if total_messages == 0:
                click.echo("No messages found in INBOX")
                return
            
            # Get recent messages (limit to 10 for testing)
            message_ids = client.search_messages("ALL")
            test_messages = message_ids[-10:] if len(message_ids) > 10 else message_ids
            
            click.echo(f"\n🧪 Testing {len(test_messages)} messages against filters...")
            click.echo(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
            click.echo("-" * 60)
            
            matches_found = 0
            
            for msg_id in test_messages:
                # Fetch message envelope
                envelopes = client.fetch_message_envelope([msg_id])
                if msg_id not in envelopes:
                    continue
                
                envelope = envelopes[msg_id]
                
                # Create MessageData object
                message_data = MessageData(
                    from_=envelope.from_[0].mailbox.decode('utf-8', errors='ignore') if envelope.from_ else None,
                    subject=envelope.subject.decode('utf-8', errors='ignore') if envelope.subject else None,
                    date=envelope.date.isoformat() if envelope.date else None,
                    size=envelope.size if hasattr(envelope, 'size') else None
                )
                
                # Test against filters
                matching_filters = filter_engine.match_message(message_data)
                
                if matching_filters:
                    matches_found += 1
                    click.echo(f"\n📧 Message {msg_id}:")
                    click.echo(f"  From: {message_data.from_}")
                    click.echo(f"  Subject: {message_data.subject}")
                    click.echo(f"  Matches: {len(matching_filters)} filter(s)")
                    
                    for filter_rule in matching_filters:
                        click.echo(f"    • {filter_rule.name} (Priority: {filter_rule.priority})")
                        for action in filter_rule.actions:
                            if action.type == 'move':
                                click.echo(f"      → Move to: {action.folder}")
                            elif action.type == 'delete':
                                click.echo(f"      → Delete message")
                            elif action.type == 'mark':
                                click.echo(f"      → Mark with: {action.flag}")
            
            click.echo(f"\n📊 Test Results:")
            click.echo(f"Messages tested: {len(test_messages)}")
            click.echo(f"Messages matching filters: {matches_found}")
            click.echo(f"Match rate: {(matches_found / len(test_messages) * 100):.1f}%")
        
        logger.info("Filter testing completed")
        
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except (IMAPConnectionError, IMAPAuthenticationError) as e:
        click.echo(f"Connection failed: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    '--config', '-c',
    type=click.Path(path_type=Path),
    help='Configuration file path (YAML). Defaults to ~/.config/IMAPMessageFilter/config.yaml'
)
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing actions')
@click.option('--folder', default='INBOX', help='Folder to process (default: INBOX)')
@click.option('--limit', type=int, help='Limit number of messages to process')
@click.option('--filter-name', help='Apply only a specific filter by name')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--cron', is_flag=True, help='Enable cron mode (file logging, no console output)')
def apply_filters(config: Optional[Path], dry_run: bool, folder: str, limit: Optional[int], filter_name: Optional[str], verbose: bool, cron: bool):
    """Apply filters to messages and execute actions."""
    try:
        # Load configuration
        config_path = str(config) if config else None
        app_config = AppConfig.load_config(config_path)
        
        # Setup logging
        if verbose:
            app_config.logging.level = "DEBUG"
        if cron:
            app_config.logging.cron_mode = True
            # Set default log file if not specified
            if not app_config.logging.file:
                app_config.logging.file = "~/.config/IMAPMessageFilter/logs/imapmessagefilter.log"
        setup_logging(app_config)
        
        logger = logging.getLogger(__name__)
        logger.info(f"Applying filters to folder: {folder}")
        
        # Initialize filter engine
        filter_engine = FilterEngine(app_config.filters.filters_path)
        
        # Connect to IMAP server
        with IMAPClientWrapper(app_config.imap) as client:
            # Select folder
            total_messages, recent_messages = client.select_folder(folder)
            
            if total_messages == 0:
                click.echo(f"No messages found in {folder}")
                return
            
            # Get messages to process
            message_ids = client.search_messages("ALL")
            if limit:
                message_ids = message_ids[-limit:]  # Process most recent messages first
            
            click.echo(f"\n🚀 Applying filters to {len(message_ids)} messages in {folder}...")
            click.echo(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
            click.echo("-" * 60)
            
            processed_count = 0
            moved_count = 0
            deleted_count = 0
            marked_count = 0
            errors = []
            
            for msg_id in message_ids:
                try:
                    # Fetch message envelope
                    envelopes = client.fetch_message_envelope([msg_id])
                    if msg_id not in envelopes:
                        continue
                    
                    envelope = envelopes[msg_id]
                    
                    # Create MessageData object
                    message_data = MessageData(
                        from_=envelope.from_[0].mailbox.decode('utf-8', errors='ignore') if envelope.from_ else None,
                        subject=envelope.subject.decode('utf-8', errors='ignore') if envelope.subject else None,
                        date=envelope.date.isoformat() if envelope.date else None,
                        size=envelope.size if hasattr(envelope, 'size') else None
                    )
                    
                    # Test against filters
                    matching_filters = filter_engine.match_message(message_data)
                    
                    # Filter by name if specified
                    if filter_name:
                        matching_filters = [f for f in matching_filters if f.name == filter_name]
                    
                    if matching_filters:
                        processed_count += 1
                        click.echo(f"\n📧 Message {msg_id}:")
                        click.echo(f"  From: {message_data.from_}")
                        click.echo(f"  Subject: {message_data.subject}")
                        click.echo(f"  Matches: {len(matching_filters)} filter(s)")
                        
                        # Execute actions for each matching filter
                        for filter_rule in matching_filters:
                            click.echo(f"    • {filter_rule.name} (Priority: {filter_rule.priority})")
                            
                            for action in filter_rule.actions:
                                if action.type == 'move':
                                    target_folder = action.folder
                                    click.echo(f"      → Move to: {target_folder}")
                                    
                                    if not dry_run:
                                        try:
                                            # Ensure target folder exists
                                            client.create_folder_if_not_exists(target_folder)
                                            # Move the message
                                            client.move_message(msg_id, target_folder)
                                            moved_count += 1
                                            click.echo(f"        ✅ Moved successfully")
                                        except Exception as e:
                                            error_msg = f"Failed to move message {msg_id}: {e}"
                                            errors.append(error_msg)
                                            click.echo(f"        ❌ {error_msg}")
                                    else:
                                        click.echo(f"        [DRY RUN] Would move to {target_folder}")
                                
                                elif action.type == 'delete':
                                    click.echo(f"      → Delete message")
                                    
                                    if not dry_run:
                                        try:
                                            client.delete_message(msg_id)
                                            deleted_count += 1
                                            click.echo(f"        ✅ Deleted successfully")
                                        except Exception as e:
                                            error_msg = f"Failed to delete message {msg_id}: {e}"
                                            errors.append(error_msg)
                                            click.echo(f"        ❌ {error_msg}")
                                    else:
                                        click.echo(f"        [DRY RUN] Would delete message")
                                
                                elif action.type == 'mark':
                                    flag = action.flag
                                    click.echo(f"      → Mark with: {flag}")
                                    
                                    if not dry_run:
                                        try:
                                            client.mark_message(msg_id, flag)
                                            marked_count += 1
                                            click.echo(f"        ✅ Marked with {flag}")
                                        except Exception as e:
                                            error_msg = f"Failed to mark message {msg_id}: {e}"
                                            errors.append(error_msg)
                                            click.echo(f"        ❌ {error_msg}")
                                    else:
                                        click.echo(f"        [DRY RUN] Would mark with {flag}")
                                
                                elif action.type == 'copy':
                                    target_folder = action.folder
                                    click.echo(f"      → Copy to: {target_folder}")
                                    
                                    if not dry_run:
                                        try:
                                            # Ensure target folder exists
                                            client.create_folder_if_not_exists(target_folder)
                                            # Copy the message
                                            client.copy_message(msg_id, target_folder)
                                            click.echo(f"        ✅ Copied successfully")
                                        except Exception as e:
                                            error_msg = f"Failed to copy message {msg_id}: {e}"
                                            errors.append(error_msg)
                                            click.echo(f"        ❌ {error_msg}")
                                    else:
                                        click.echo(f"        [DRY RUN] Would copy to {target_folder}")
                
                except Exception as e:
                    error_msg = f"Error processing message {msg_id}: {e}"
                    errors.append(error_msg)
                    click.echo(f"❌ {error_msg}")
            
            # Summary
            click.echo(f"\n📊 Filter Application Results:")
            click.echo(f"Messages processed: {processed_count}")
            click.echo(f"Messages moved: {moved_count}")
            click.echo(f"Messages deleted: {deleted_count}")
            click.echo(f"Messages marked: {marked_count}")
            
            if errors:
                click.echo(f"\n❌ Errors ({len(errors)}):")
                for error in errors[:5]:  # Show first 5 errors
                    click.echo(f"  • {error}")
                if len(errors) > 5:
                    click.echo(f"  ... and {len(errors) - 5} more errors")
        
        logger.info("Filter application completed")
        
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except (IMAPConnectionError, IMAPAuthenticationError) as e:
        click.echo(f"Connection failed: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()
