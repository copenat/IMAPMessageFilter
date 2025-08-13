"""Command-line interface for IMAP Message Filter."""

import logging
import sys
from pathlib import Path
from typing import Optional

import click

from .config import AppConfig
from .imap_client import IMAPClientWrapper, IMAPConnectionError, IMAPAuthenticationError


def setup_logging(config: AppConfig) -> None:
    """Setup logging configuration."""
    log_config = {
        'level': getattr(logging, config.logging.level),
        'format': config.logging.format,
        'handlers': [logging.StreamHandler(sys.stdout)]
    }
    
    if config.logging.file:
        log_config['handlers'].append(
            logging.FileHandler(config.logging.file, encoding='utf-8')
        )
    
    logging.basicConfig(**log_config)


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


if __name__ == '__main__':
    cli()
