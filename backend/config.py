from functools import lru_cache
from pydantic_settings import BaseSettings,SettingsConfigDict
class Settings(BaseSettings):
 model_config=SettingsConfigDict(env_file='.env',extra='ignore')
 DATABASE_URL:str='sqlite:///./eventhub.db'; JWT_SECRET:str='dev'; PASS_SECRET:str='devpass'; RAZORPAY_KEY_ID:str=''; RAZORPAY_KEY_SECRET:str=''; RAZORPAY_WEBHOOK_SECRET:str=''; ADMIN_USERNAME:str='admin'; ADMIN_PASSWORD:str='admin123'; SCANNER_KEY:str='gate-a-dev-key'; PUBLIC_BASE_URL:str='http://127.0.0.1:8000'; ALLOW_EARLY_SCAN:bool=True
@lru_cache
def get_settings(): return Settings()
