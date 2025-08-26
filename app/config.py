import os
from functools import lru_cache


class Settings:
    base_iri: str
    data_ttl_path: str
    default_language: str

    def __init__(self) -> None:
        self.base_iri = os.getenv("BASE_IRI", "https://vocabulary.montessoriglossary.org/")
        self.data_ttl_path = os.getenv("DATA_TTL_PATH", os.path.abspath(os.path.join(os.getcwd(), "data", "vocabulary.ttl")))
        self.default_language = os.getenv("DEFAULT_LANGUAGE", "en")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()