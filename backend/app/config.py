from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str = ''
    supabase_key: str = ''
    redis_url: str = 'redis://localhost:6379/0'
    spiderfoot_url: str = 'http://localhost:5001'
    admin_password: str = 'change-me-before-deploying'

    class Config:
        env_file = '.env'


settings = Settings()
