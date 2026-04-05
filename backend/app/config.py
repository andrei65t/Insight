from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Insight B2B"

    # Supabase config
    SUPABASE_URL: str = "https://nxkjiukvmeqwwdwktucl.supabase.co"
    SUPABASE_ANON_KEY: str = "sb_publishable_M4WXor5VF__0wUVPT402bA_Ym8Ta_nO"
    SUPABASE_SERVICE_ROLE_KEY: str = "SECRET_KEY"
    TRACKING_TABLE: str = "user_tracked_companies"

    class Config:
        case_sensitive = True


settings = Settings()
