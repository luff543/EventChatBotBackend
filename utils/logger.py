import logging
import sys
from datetime import datetime
import codecs
import os

# 確保logs目錄存在
os.makedirs('logs', exist_ok=True)

# Create logger
logger = logging.getLogger('event_chatbot')
logger.setLevel(logging.DEBUG)

# Create console handler with formatting
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)

# Create file handler with formatting
file_handler = logging.FileHandler(
    f'logs/event_chatbot_{datetime.now().strftime("%Y%m%d")}.log',
    encoding='utf-8'  # 指定 UTF-8 編碼
)
file_handler.setLevel(logging.DEBUG)

# Create formatter with line numbers
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Add formatter to handlers
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# 設置 stdout 的編碼為 utf-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict') 