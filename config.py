class Config:
    API_KEY = "your_api_key_here"
    MENU_FILE_PATH = "src/data/menu.json"
    UPSELLING_RULES_FILE_PATH = "src/data/upselling_rules.json"
    DEFAULT_LANGUAGE = "en"
    MAX_ORDER_ITEMS = 5
    UPSELLING_THRESHOLD = 3
    TIMEOUT_DURATION = 30  # seconds for user response timeout
    LOGGING_LEVEL = "INFO"  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
    DATABASE_URL = "sqlite:///restaurant_orders.db"  # Example database URL for order storage