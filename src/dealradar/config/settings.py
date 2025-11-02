"""
Configuration settings for DealRadar
Centralizes all constants and environment variables
"""
import os
from typing import Dict


class Settings:
    """Application settings"""

    # Blocket API Configuration
    SITE_URL: str = "https://www.blocket.se"
    API_URL: str = "https://api.blocket.se"
    USER_AGENT: str = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"

    # Database Configuration
    DB_HOST: str = os.getenv('DB_HOST', 'localhost')
    DB_PORT: str = os.getenv('DB_PORT', '5432')
    DB_NAME: str = os.getenv('DB_NAME', 'dealradar')
    DB_USER: str = os.getenv('DB_USER', 'dealradar')
    DB_PASSWORD: str = os.getenv('DB_PASSWORD', 'dealradar')

    # API Rate Limiting
    DEFAULT_BATCH_SIZE: int = 3
    BATCH_DELAY_SECONDS: float = 0.5
    API_TIMEOUT_SECONDS: float = 30.0

    # Blocket Category IDs
    CATEGORIES: Dict[str, str] = {
        'computers': '5021',
        'computer_accessories': '5020',
        'mobile_phones': '5040',
        'gaming_consoles': '5060',
        'furniture': '40',
        'vehicles': '10',
    }

    # Evaluation Settings
    HIGH_VALUE_THRESHOLD: int = 8
    DEFAULT_SEARCH_LIMIT: int = 10
    MAX_SEARCH_LIMIT: int = 100

    @property
    def db_config(self) -> Dict[str, str]:
        """Get database configuration as dictionary"""
        return {
            'host': self.DB_HOST,
            'port': self.DB_PORT,
            'database': self.DB_NAME,
            'user': self.DB_USER,
            'password': self.DB_PASSWORD
        }

    def get_category_id(self, name: str) -> str:
        """Get category ID by name"""
        return self.CATEGORIES.get(name.lower())


# Global settings instance
settings = Settings()
