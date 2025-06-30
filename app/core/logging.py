import logging
import sys
import warnings
from typing import Dict, Any

def setup_logging():
    """Thiết lập logging cho ứng dụng"""
    
    # Suppress specific warnings
    warnings.filterwarnings("ignore", message="file_cache is only supported with oauth2client<4.0.0")
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="googleapiclient")
    
    # Cấu hình root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Cấu hình specific loggers
    loggers_to_configure: Dict[str, Any] = {
        "uvicorn": {"level": logging.INFO},
        "uvicorn.error": {"level": logging.INFO},
        "uvicorn.access": {"level": logging.WARNING},
        "googleapiclient": {"level": logging.WARNING},
        "googleapiclient.discovery_cache": {"level": logging.WARNING},
        "app": {"level": logging.INFO},
    }
    
    for logger_name, config in loggers_to_configure.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(config["level"])
        
        # Prevent duplicate handlers
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            logger.addHandler(handler)
    
    # Disable propagation for some noisy loggers
    logging.getLogger("googleapiclient.discovery_cache").propagate = False
    
    logging.info("Logging configuration completed") 