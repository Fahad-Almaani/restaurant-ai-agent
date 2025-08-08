class Config:
    # API Configuration
    API_KEY = "your_api_key_here"
    
    # AI Model Configuration
    MODEL_NAME = "gemma-3-27b-it"
    MODEL_TEMPERATURE = 0.7
    MAX_TOKENS = 1000
    
    # File Paths
    MENU_FILE_PATH = "src/data/menu.json"
    UPSELLING_RULES_FILE_PATH = "src/data/upselling_rules.json"
    
    # Application Settings
    DEFAULT_LANGUAGE = "en"
    MAX_ORDER_ITEMS = 5
    UPSELLING_THRESHOLD = 3
    TIMEOUT_DURATION = 30  # seconds for user response timeout
    LOGGING_LEVEL = "INFO"  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
    DATABASE_URL = "sqlite:///restaurant_orders.db"  # Example database URL for order storage