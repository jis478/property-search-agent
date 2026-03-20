from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Optional: Google Maps API key for school-distance enrichment (Geocoding + Distance Matrix)
    google_maps_api_key: str = ""

    # # Stubbed for later phases — all optional in Phase 1
    # openai_api_key: str = ""
    # langfuse_secret_key: str = ""
    # langfuse_host: str = "https://cloud.langfuse.com"


settings = Settings()
