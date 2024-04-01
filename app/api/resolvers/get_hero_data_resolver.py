"""Hero Request Handler module"""

from typing import ClassVar

from app.config import settings
from app.parsers.hero_parser import HeroParser
from app.parsers.heroes_parser import HeroesParser
from app.parsers.heroes_stats_parser import HeroesStatsParser
from app.utils.helpers import dict_insert_value_before_key

from .base_data_resolver import BaseDataResolver


class GetHeroDataResolver(BaseDataResolver):
    """Hero Request Handler used in order to retrieve data about a single
    Overwatch hero. The hero key given by the ListHeroesDataResolver
    should be used to display data about a specific hero.
    """

    parser_classes: ClassVar[list] = [HeroParser, HeroesParser, HeroesStatsParser]
    timeout = settings.hero_path_cache_timeout

    def fetch_data_from_database(self, **kwargs) -> None:
        # Fetch hero data in db, store it in self.data
        # Filters are always being used here, list heroes = role filter
        pass

    def fetch_process_store_data(self, **kwargs) -> None:
        # self.data = already fetched data
        # Fetchers ? HeroesListFetcher, SpecificHeroFetcher, etc.
        # if not portrait_value (no key at all)
        # Fetch heroes list
        # if not single
        # Fetch single hero Blizzard page, store in DB
        # if not some csv data for some reason (hitpoints key)
        # Fetch CSV data

    def merge_parsers_data(self, parsers_data: list[dict], **kwargs) -> dict:
        """Merge parsers data together :
        - HeroParser for detailed data
        - HeroesParser for portrait (not here in the specific page)
        - HeroesStatsParser for stats (health, armor, shields)
        """
        hero_data, heroes_data, heroes_stats_data = parsers_data

        try:
            portrait_value = next(
                hero["portrait"]
                for hero in heroes_data
                if hero["key"] == kwargs.get("hero_key")
            )
        except StopIteration:
            # The hero key may not be here in some specific edge cases,
            # for example if the hero has been released but is not in the
            # heroes list yet, or the list cache is outdated
            portrait_value = None
        else:
            # We want to insert the portrait before the "role" key
            hero_data = dict_insert_value_before_key(
                hero_data,
                "role",
                "portrait",
                portrait_value,
            )

        try:
            hitpoints = heroes_stats_data[kwargs.get("hero_key")]["hitpoints"]
        except KeyError:
            # Hero hitpoints may not be here if the CSV file
            # containing the data hasn't been updated
            hitpoints = None
        else:
            # We want to insert hitpoints before "abilities" key
            hero_data = dict_insert_value_before_key(
                hero_data,
                "abilities",
                "hitpoints",
                hitpoints,
            )

        return hero_data
