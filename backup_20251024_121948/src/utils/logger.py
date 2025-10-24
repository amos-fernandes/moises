import logging
import logging.handlers
import json
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_DIR = "logs"
LOG_FILE = f"{LOG_DIR}/atcoin_{datetime.utcnow().strftime('%Y-%m-%d')}.log"

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "name": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        return json.dumps(log_record)

def get_logger(name: str = "atcoin"):
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    formatter = JsonFormatter()

    # Evita múltiplos handlers duplicados
    if not logger.handlers:
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            file_handler = logging.handlers.TimedRotatingFileHandler(
                LOG_FILE, when="midnight", backupCount=7, encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            # Fallback para stderr
            stream_handler = logging.StreamHandler(sys.stderr)
            stream_handler.setFormatter(formatter)
            logger.addHandler(stream_handler)
            logger.warning(f"Falha ao configurar arquivo de log: {e}")
    
    return logger
