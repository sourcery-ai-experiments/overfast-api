"""List Heroes Request Handler module"""

from typing import ClassVar

from app.config import settings
from app.parsers.heroes_parser import HeroesParser

from .base_data_resolver import BaseDataResolver


class ListHeroesDataResolver(BaseDataResolver):
    """List Heroes Request Handler used in order to
    retrieve a list of available Overwatch heroes.
    """

    parser_classes: ClassVar[list] = [HeroesParser]
    timeout = settings.heroes_path_cache_timeout

    def fetch_data_from_database(self, **kwargs):
        # Filters are always being used here, list heroes = role filter
        pass

    def fetch_process_store_data(self, **kwargs):
        # Fetch ALL heroes, regardless of filter
        pass
