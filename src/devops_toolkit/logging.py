"""
DevOps Toolkit - Logging Module

This module provides a centralized logging system for the entire toolkit,
supporting console and file logging with configurable levels.
"""
import os
import sys
import logging
import logging.handlers
import json
from datetime import datetime
from typing import Dict, Any, Optional, Union, List

# Try to import rich for enhanced console output
try:
    from rich.logging import RichHandler
    from rich.console import Console
    from rich.traceback import install as install_rich_traceback
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Local imports
from devops_toolkit.config import get_config


class StructuredLogFormatter(logging.Formatter):
    """
    Formatter for structured JSON logging.
    """

    def __init__(self, include_timestamp: bool = True):
        """
        Initialize formatter.

        Args:
            include_timestamp: Whether to include timestamp in logs
        """
        super().__init__()
        self.include_timestamp = include_timestamp

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        log_data = {
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        if self.include_timestamp:
            log_data['timestamp'] = datetime.utcfromtimestamp(record.created).isoformat() + 'Z'

        # Add exception info if available
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Add extra fields if available
        if hasattr(record, 'data') and record.data:
            log_data['data'] = record.data

        return json.dumps(log_data)


class CustomLogger(logging.Logger):
    """
    Extended logger class with additional methods for structured logging.
    """

    def __init__(self, name: str, level: int = logging.NOTSET):
        """
        Initialize custom logger.

        Args:
            name: Logger name
            level: Initial logging level
        """
        super().__init__(name, level)

    def struct(self, msg: str, data: Dict[str, Any], level: int = logging.INFO) -> None:
        """
        Log a structured message with additional data.

        Args:
            msg: Log message
            data: Additional data to include in log
            level: Log level
        """
        if self.isEnabledFor(level):
            record = self.makeRecord(
                self.name, level, "", 0, msg, (), None
            )
            record.data = data
            self.handle(record)

    def success(self, msg: str, *args, **kwargs) -> None:
        """
        Log a success message (using INFO level).

        Args:
            msg: Log message
            args: Additional positional arguments
            kwargs: Additional keyword arguments
        """
        self.info(f"✅ {msg}", *args, **kwargs)

    def start(self, msg: str, *args, **kwargs) -> None:
        """
        Log a task start message (using INFO level).

        Args:
            msg: Log message
            args: Additional positional arguments
            kwargs: Additional keyword arguments
        """
        self.info(f"▶️ {msg}", *args, **kwargs)

    def complete(self, msg: str, *args, **kwargs) -> None:
        """
        Log a task completion message (using INFO level).

        Args:
            msg: Log message
            args: Additional positional arguments
            kwargs: Additional keyword arguments
        """
        self.info(f"✓ {msg}", *args, **kwargs)

    def failure(self, msg: str, *args, **kwargs) -> None:
        """
        Log a failure message (using ERROR level).

        Args:
            msg: Log message
            args: Additional positional arguments
            kwargs: Additional keyword arguments
        """
        self.error(f"❌ {msg}", *args, **kwargs)


# Register custom logger class
logging.setLoggerClass(CustomLogger)


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    json_format: bool = False,
    module_levels: Optional[Dict[str, str]] = None
) -> None:
    """
    Set up logging for the application.

    Args:
        level: Default log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (if None, only console logging is used)
        json_format: Whether to use JSON format for logs
        module_levels: Dict of module names to log levels
    """
    # Convert string level to logging level
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Use Rich for console logging if available, otherwise use standard StreamHandler
    if RICH_AVAILABLE:
        # Install rich traceback handler
        install_rich_traceback(show_locals=True)

        # Create console handler with Rich
        console_handler = RichHandler(
            rich_tracebacks=True,
            markup=True,
            show_time=False,
            omit_repeated_times=False
        )
    else:
        # Create standard console handler
        console_handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
        console_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)

    # Add file handler if log file is specified
    if log_file:
        # Create log directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        # Create file handler with appropriate formatter
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5
        )

        if json_format:
            file_handler.setFormatter(StructuredLogFormatter())
        else:
            file_handler.setFormatter(
                logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
            )

        root_logger.addHandler(file_handler)

    # Set module-specific log levels if provided
    if module_levels:
        for module, level in module_levels.items():
            module_logger = logging.getLogger(module)
            module_logger.setLevel(getattr(logging, level.upper(), numeric_level))

    # Log startup information
    logger = logging.getLogger("devops_toolkit")
    logger.info(f"Logging initialized at {level} level")
    if log_file:
        logger.info(f"Log file: {log_file}")


def get_logger(name: str) -> CustomLogger:
    """
    Get a logger for a specific module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def init_logging_from_config() -> None:
    """
    Initialize logging using configuration from config file.
    """
    try:
        config = get_config()
        global_config = config.get_global()

        # Get logging configuration
        log_level = global_config.log_level
        log_file = global_config.log_file

        # Set up logging
        setup_logging(level=log_level, log_file=log_file)
    except Exception as e:
        # Fall back to basic logging if configuration fails
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger("devops_toolkit")
        logger.error(f"Error initializing logging from config: {str(e)}")
        logger.info("Falling back to basic logging configuration")
