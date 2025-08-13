"""Tests for configuration module."""

import pytest
from pydantic import ValidationError

from imapmessagefilter.config import IMAPServerConfig, LoggingConfig, AppConfig


class TestIMAPServerConfig:
    """Test IMAP server configuration."""
    
    def test_valid_config(self):
        """Test valid IMAP server configuration."""
        config = IMAPServerConfig(
            host="imap.gmail.com",
            port=993,
            username="test@example.com",
            password="password123",
            use_ssl=True,
            timeout=30
        )
        
        assert config.host == "imap.gmail.com"
        assert config.port == 993
        assert config.username == "test@example.com"
        assert config.password == "password123"
        assert config.use_ssl is True
        assert config.timeout == 30
    
    def test_invalid_port(self):
        """Test invalid port number."""
        with pytest.raises(ValidationError):
            IMAPServerConfig(
                host="imap.gmail.com",
                port=70000,  # Invalid port
                username="test@example.com",
                password="password123"
            )
    
    def test_invalid_timeout(self):
        """Test invalid timeout value."""
        with pytest.raises(ValidationError):
            IMAPServerConfig(
                host="imap.gmail.com",
                port=993,
                username="test@example.com",
                password="password123",
                timeout=0  # Invalid timeout
            )


class TestLoggingConfig:
    """Test logging configuration."""
    
    def test_valid_config(self):
        """Test valid logging configuration."""
        config = LoggingConfig(
            level="INFO",
            format="%(asctime)s - %(message)s",
            file=None
        )
        
        assert config.level == "INFO"
        assert config.format == "%(asctime)s - %(message)s"
        assert config.file is None
    
    def test_invalid_level(self):
        """Test invalid logging level."""
        with pytest.raises(ValidationError):
            LoggingConfig(level="INVALID_LEVEL")
    
    def test_case_insensitive_level(self):
        """Test case-insensitive logging level."""
        config = LoggingConfig(level="debug")
        assert config.level == "DEBUG"


class TestAppConfig:
    """Test application configuration."""
    
    def test_valid_config(self):
        """Test valid application configuration."""
        config = AppConfig(
            imap=IMAPServerConfig(
                host="imap.gmail.com",
                port=993,
                username="test@example.com",
                password="password123"
            ),
            logging=LoggingConfig()
        )
        
        assert config.imap.host == "imap.gmail.com"
        assert config.logging.level == "INFO"
    
    def test_default_logging(self):
        """Test default logging configuration."""
        config = AppConfig(
            imap=IMAPServerConfig(
                host="imap.gmail.com",
                port=993,
                username="test@example.com",
                password="password123"
            )
        )
        
        assert config.logging.level == "INFO"
        assert "asctime" in config.logging.format
