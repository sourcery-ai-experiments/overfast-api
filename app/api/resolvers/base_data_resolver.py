"""Abstract API Request Handler module"""

from abc import ABC, abstractmethod

from fastapi import HTTPException, Request

from app.api.exceptions import ParserBlizzardError, ParserParsingError
from app.database.cache_manager import CacheManager
from app.utils.helpers import overfast_internal_error
from app.utils.logging import logger


class BaseDataResolver(ABC):
    """Generic Base Data Resolver, containing attributes structure and methods
    in order to quickly be able to create concrete data resolvers. A resolver can
    be associated with several parsers (one parser = one Blizzard page parsing).
    The API Cache system is handled here.
    """

    # Generic cache manager class, used to manipulate Redis cache data
    cache_manager = CacheManager()

    def __init__(self, request: Request):
        self.cache_key = CacheManager.get_cache_key_from_request(request)

    @property
    @abstractmethod
    def parser_classes(self) -> type:
        """Parser classes used for parsing the Blizzard page retrieved with this handler"""

    @property
    @abstractmethod
    def timeout(self) -> int:
        """Timeout used for API Cache storage for this specific handler"""

    async def process_query(self, **kwargs) -> dict:
        """Main method used to process the request from user and return final data.
        Raises an HTTPException in case of error when retrieving or parsing data.

        The main steps are :
        - Instanciate the dedicated parser classes, each one will :
            - Check if Parser Cache is available. If so, use it
            - Else, get Blizzard HTML page, parse it and create the Parser Cache
        - Filter the data using kwargs parameters, then merge the data from parsers
        - Update related API Cache and return the final data
        """

        # First check for data in database
        logger.info("Fetching data from database...")
        fetched_data = self.fetch_data_from_database(**kwargs)

        # If no data is here, fetch the data from scratch
        if not fetched_data:
            logger.info("No data in DB, fetching from data sources...")
            fetched_data = self.fetch_process_store_data(**kwargs)

        # Update API Cache
        self.cache_manager.update_api_cache(self.cache_key, fetched_data, self.timeout)

        logger.info("Done ! Returning data...")
        return fetched_data

    def fetch_data_from_database(self, **kwargs):
        """Retrieve data from database directly, assuming it's up-to-date"""

    def fetch_process_store_data(self, **kwargs):
        """Fetch, process and store the data for the given query"""

    def retrieve_data_from_blizzard(self, **kwargs):
        # Request the data from Blizzard page
        parsers_data = []
        for parser_class in self.parser_classes:
            # Instanciate the parser, it will check if a Parser Cache is here.
            # If not, it will retrieve its associated Blizzard
            # page and use the kwargs to generate the appropriate URL
            parser = parser_class(**kwargs)

            # Do the parsing. Internally, it will check for Parser Cache
            # before doing a real parsing using BeautifulSoup
            try:
                await parser.parse()
            except ParserBlizzardError as error:
                raise HTTPException(
                    status_code=error.status_code,
                    detail=error.message,
                ) from error
            except ParserParsingError as error:
                raise overfast_internal_error(parser.blizzard_url, error) from error

            # Filter the data to obtain final parser data
            logger.info("Filtering the data using query...")
            parsers_data.append(parser.filter_request_using_query(**kwargs))
