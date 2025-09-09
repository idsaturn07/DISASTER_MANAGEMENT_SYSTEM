"""
Configuration management for Disaster Management System
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration"""
    
    # Flask Configuration
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'disaster_is_the_key')
    
    # Supabase Configuration
    SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')
    
    # Weather API Configuration (Optional)
    WEATHER_API_KEY = os.environ.get('WEATHER_API_KEY', '')
    
    @classmethod
    def is_supabase_configured(cls):
        """Check if Supabase is properly configured"""
        return bool(cls.SUPABASE_URL and cls.SUPABASE_KEY)
    
    @classmethod
    def is_weather_api_configured(cls):
        """Check if weather API is configured (optional)"""
        return bool(cls.WEATHER_API_KEY and cls.WEATHER_API_KEY != 'your_openweathermap_api_key_here')
    
    @classmethod
    def get_config_status(cls):
        """Get configuration status for debugging"""
        return {
            'supabase_configured': cls.is_supabase_configured(),
            'weather_api_configured': cls.is_weather_api_configured(),
            'supabase_url_set': bool(cls.SUPABASE_URL),
            'supabase_key_set': bool(cls.SUPABASE_KEY),
            'weather_api_key_set': bool(cls.WEATHER_API_KEY)
        }