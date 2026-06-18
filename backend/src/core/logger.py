import os
from logging.config import dictConfig
from pathlib import Path

LOG_DIR = Path(os.getenv('LOG_DIR', 'logs'))
LOG_DIR.mkdir(parents=True, exist_ok=True)

BASE_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'base': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'datefmt': '%d-%m-%Y %H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'base',
            'level': 'INFO',
            'stream': 'ext://sys.stdout',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'formatter': 'base',
            'filename': str(LOG_DIR / 'app_modules.log'),
            'maxBytes': 10485760,
            'backupCount': 5,
            'encoding': 'utf8',
        },
        'third_party_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'formatter': 'base',
            'filename': str(LOG_DIR / 'app_third_party.log'),
            'maxBytes': 10485760,
            'backupCount': 5,
            'encoding': 'utf8',
        },
    },
    'loggers': {
        'src': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console', 'third_party_file'],
        'level': 'INFO',
    },
}

dictConfig(BASE_CONFIG)
