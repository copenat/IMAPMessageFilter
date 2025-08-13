"""IMAP client for connecting to mail servers and basic operations."""

import logging
from typing import List, Optional, Tuple

from imapclient import IMAPClient
from imapclient.exceptions import IMAPClientError

from .config import IMAPServerConfig


class IMAPConnectionError(Exception):
    """Raised when IMAP connection fails."""
    pass


class IMAPAuthenticationError(Exception):
    """Raised when IMAP authentication fails."""
    pass


class IMAPClientWrapper:
    """Wrapper for IMAPClient with error handling and logging."""
    
    def __init__(self, config: IMAPServerConfig):
        """Initialize IMAP client with configuration."""
        self.config = config
        self.client: Optional[IMAPClient] = None
        self.logger = logging.getLogger(__name__)
    
    def connect(self) -> None:
        """Connect to IMAP server."""
        try:
            self.logger.info(f"Connecting to IMAP server: {self.config.host}:{self.config.port}")
            
            if self.config.use_ssl:
                # SSL/TLS connection (port 993 typically)
                self.logger.info("Using SSL/TLS connection")
                self.client = IMAPClient(
                    self.config.host,
                    port=self.config.port,
                    ssl=True,
                    timeout=self.config.timeout
                )
            elif self.config.use_starttls:
                # STARTTLS connection (port 143 typically)
                self.logger.info("Using STARTTLS connection")
                self.client = IMAPClient(
                    self.config.host,
                    port=self.config.port,
                    ssl=False,
                    timeout=self.config.timeout
                )
                # Start TLS after connection
                try:
                    self.client.starttls()
                    self.logger.info("STARTTLS negotiation completed")
                except Exception as e:
                    if "DH_KEY_TOO_SMALL" in str(e) and self.config.allow_insecure:
                        self.logger.warning("Server uses weak DH key, allowing insecure connection")
                        # Continue without TLS for legacy servers
                        pass
                    else:
                        raise
            else:
                # Unencrypted connection
                self.logger.info("Using unencrypted connection")
                self.client = IMAPClient(
                    self.config.host,
                    port=self.config.port,
                    ssl=False,
                    timeout=self.config.timeout
                )
            
            self.logger.info("IMAP connection established successfully")
            
        except IMAPClientError as e:
            self.logger.error(f"Failed to connect to IMAP server: {e}")
            raise IMAPConnectionError(f"Connection failed: {e}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error during connection: {e}")
            raise IMAPConnectionError(f"Unexpected connection error: {e}") from e
    
    def authenticate(self) -> None:
        """Authenticate with IMAP server."""
        if not self.client:
            raise IMAPConnectionError("Not connected to IMAP server")
        
        try:
            self.logger.info(f"Authenticating as user: {self.config.username}")
            self.client.login(self.config.username, self.config.password)
            self.logger.info("Authentication successful")
            
        except IMAPClientError as e:
            self.logger.error(f"Authentication failed: {e}")
            raise IMAPAuthenticationError(f"Authentication failed: {e}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error during authentication: {e}")
            raise IMAPAuthenticationError(f"Unexpected authentication error: {e}") from e
    
    def list_folders(self) -> List[str]:
        """List all available folders."""
        if not self.client:
            raise IMAPConnectionError("Not connected to IMAP server")
        
        try:
            folders = self.client.list_folders()
            folder_names = [folder[2] for folder in folders]
            self.logger.info(f"Found {len(folder_names)} folders")
            return folder_names
            
        except IMAPClientError as e:
            self.logger.error(f"Failed to list folders: {e}")
            raise IMAPConnectionError(f"Failed to list folders: {e}") from e
    
    def select_folder(self, folder_name: str) -> Tuple[int, int]:
        """Select a folder and return message count information."""
        if not self.client:
            raise IMAPConnectionError("Not connected to IMAP server")
        
        try:
            self.logger.info(f"Selecting folder: {folder_name}")
            folder_info = self.client.select_folder(folder_name)
            
            total_messages = folder_info[b'EXISTS']
            recent_messages = folder_info.get(b'RECENT', 0)
            
            self.logger.info(f"Folder '{folder_name}' selected: {total_messages} total, {recent_messages} recent")
            return total_messages, recent_messages
            
        except IMAPClientError as e:
            self.logger.error(f"Failed to select folder '{folder_name}': {e}")
            raise IMAPConnectionError(f"Failed to select folder: {e}") from e
    
    def search_messages(self, criteria: str = "ALL") -> List[int]:
        """Search for messages using IMAP search criteria."""
        if not self.client:
            raise IMAPConnectionError("Not connected to IMAP server")
        
        try:
            self.logger.info(f"Searching messages with criteria: {criteria}")
            message_ids = self.client.search(criteria)
            self.logger.info(f"Found {len(message_ids)} messages matching criteria")
            return message_ids
            
        except IMAPClientError as e:
            self.logger.error(f"Failed to search messages: {e}")
            raise IMAPConnectionError(f"Failed to search messages: {e}") from e
    
    def fetch_message_headers(self, message_ids: List[int]) -> dict:
        """Fetch message headers for given message IDs."""
        if not self.client:
            raise IMAPConnectionError("Not connected to IMAP server")
        
        if not message_ids:
            return {}
        
        try:
            self.logger.info(f"Fetching headers for {len(message_ids)} messages")
            headers = self.client.fetch(message_ids, ['RFC822.HEADER'])
            
            result = {}
            for msg_id, data in headers.items():
                if b'RFC822.HEADER' in data:
                    result[msg_id] = data[b'RFC822.HEADER'].decode('utf-8', errors='ignore')
            
            self.logger.info(f"Successfully fetched headers for {len(result)} messages")
            return result
            
        except IMAPClientError as e:
            self.logger.error(f"Failed to fetch message headers: {e}")
            raise IMAPConnectionError(f"Failed to fetch headers: {e}") from e
    
    def fetch_message_envelope(self, message_ids: List[int]) -> dict:
        """Fetch message envelope information for given message IDs."""
        if not self.client:
            raise IMAPConnectionError("Not connected to IMAP server")
        
        if not message_ids:
            return {}
        
        try:
            self.logger.info(f"Fetching envelope for {len(message_ids)} messages")
            envelopes = self.client.fetch(message_ids, ['ENVELOPE'])
            
            result = {}
            for msg_id, data in envelopes.items():
                if b'ENVELOPE' in data:
                    result[msg_id] = data[b'ENVELOPE']
            
            self.logger.info(f"Successfully fetched envelope for {len(result)} messages")
            return result
            
        except IMAPClientError as e:
            self.logger.error(f"Failed to fetch message envelope: {e}")
            raise IMAPConnectionError(f"Failed to fetch envelope: {e}") from e
    
    def disconnect(self) -> None:
        """Disconnect from IMAP server."""
        if self.client:
            try:
                self.client.logout()
                self.logger.info("Disconnected from IMAP server")
            except Exception as e:
                self.logger.warning(f"Error during logout: {e}")
            finally:
                self.client = None
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        self.authenticate()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
