"""Configuration management for IMAP Message Filter."""

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict
from pydantic_settings import BaseSettings


class IMAPServerConfig(BaseModel):
    """Configuration for IMAP server connection."""
    
    host: str = Field(..., description="IMAP server hostname")
    port: int = Field(993, description="IMAP server port")
    username: str = Field(..., description="IMAP username/email")
    password: str = Field(..., description="IMAP password")
    use_ssl: bool = Field(True, description="Use SSL/TLS connection")
    use_starttls: bool = Field(False, description="Use STARTTLS connection")
    allow_insecure: bool = Field(False, description="Allow insecure connections for legacy servers")
    timeout: int = Field(30, description="Connection timeout in seconds")
    
    @field_validator('port')
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port number."""
        if not 1 <= v <= 65535:
            raise ValueError('Port must be between 1 and 65535')
        return v
    
    @field_validator('timeout')
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate timeout value."""
        if v <= 0:
            raise ValueError('Timeout must be positive')
        return v


class LoggingConfig(BaseModel):
    """Configuration for logging."""
    
    level: str = Field("INFO", description="Logging level")
    format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )
    file: Optional[str] = Field(None, description="Log file path")
    
    @field_validator('level')
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate logging level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {valid_levels}')
        return v.upper()


class AppConfig(BaseSettings):
    """Main application configuration."""
    
    imap: IMAPServerConfig
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    model_config = ConfigDict(
        env_prefix="IMAPMESSAGEFILTER_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8"
    )
    
    @classmethod
    def get_default_config_path(cls) -> Path:
        """Get the default configuration file path."""
        return Path.home() / ".config" / "IMAPMessageFilter" / "config.yaml"
    
    @classmethod
    def load_config(cls, config_path: Optional[str] = None) -> "AppConfig":
        """Load configuration from file or default location."""
        if config_path:
            file_path = Path(config_path)
        else:
            file_path = cls.get_default_config_path()
        
        if not file_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {file_path}\n"
                f"Please create the configuration file at: {file_path}\n"
                f"Or specify a different path with --config option"
            )
        
        return cls.from_yaml(str(file_path))
    
    @classmethod
    def from_yaml(cls, file_path: str) -> "AppConfig":
        """Load configuration from YAML file."""
        import yaml
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        return cls(**config_data)
