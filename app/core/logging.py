import logging
import re
import sys
from typing import Optional, Dict

_CONFIGURED_LOGGERS: Dict[str, logging.Logger] = {}

_SENSITIVE_PATTERNS = [
    (re.compile(r'(api[_-]?key|token|password|secret)["\']?\s*[=:]\s*["\']?([^"\'\s,}{]+)', re.IGNORECASE), r'\1=***'),
    (re.compile(r'(admin-key-[a-zA-Z0-9]{1,8})([a-zA-Z0-9-]+)'), r'\1***'),
    (re.compile(r'(key-[a-zA-Z0-9]{1,8})([a-zA-Z0-9-]+)'), r'\1***'),
]

class SensitiveDataFilter(logging.Filter):

    def filter(self, record):
        if isinstance(record.msg, str):
            for pattern, replacement in _SENSITIVE_PATTERNS:
                record.msg = pattern.sub(replacement, record.msg)
        
        if hasattr(record, 'args') and record.args:
            args = list(record.args)
            for i, arg in enumerate(args):
                if isinstance(arg, str):
                    for pattern, replacement in _SENSITIVE_PATTERNS:
                        args[i] = pattern.sub(replacement, arg)
            record.args = tuple(args)
            
        return True

def setup_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    if name in _CONFIGURED_LOGGERS:
        return _CONFIGURED_LOGGERS[name]
    
    if level is None:
        level = logging.INFO
        
    logger = logging.getLogger(name)
    
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    logger.setLevel(level)
    logger.propagate = False
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    
    sensitive_filter = SensitiveDataFilter()
    handler.addFilter(sensitive_filter)
    
    logger.addHandler(handler)
    
    _CONFIGURED_LOGGERS[name] = logger
    
    return logger

def configure_root_logger(level: int = logging.INFO):
    root_logger = logging.getLogger()
    
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    root_logger.setLevel(level)
    
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    app_logger = setup_logger("app", level)
    
    return app_logger

app_logger = configure_root_logger()
