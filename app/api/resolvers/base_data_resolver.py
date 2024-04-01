"""Abstract API Request Handler module"""

from abc import ABC, abstractmethod
from typing import ClassVar

from fastapi import HTTPException, Request
from pydantic import ValidationError

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

    cache_key: str
    response_model: ClassVar

    def __init__(self, request: Request, response_model: ClassVar):
        self.cache_key = CacheManager.get_cache_key_from_request(request)
        self.response_model = response_model

    @property
    @abstractmethod
    def parser_classes(self) -> type:
        """Parser classes used for parsing the Blizzard page retrieved with this handler"""

    @property
    @abstractmethod
    def timeout(self) -> int:
        """Timeout used for API Cache storage for this specific handler"""

    @abstractmethod
    def fetch_data_from_database(self, **kwargs) -> None:
        """Retrieve data from database directly, assuming it's up-to-date"""

    @abstractmethod
    def fetch_process_store_data(self, **kwargs) -> None:
        """Fetch, process and store the data for the given query"""

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
        logger.info("Fetching data from DB...")
        self.fetch_data_from_database(**kwargs)

        # Validate data (check if OK to do so before filtering)
        try:
            self.check_data_integrity()
        except ValidationError:
            # There is no data or insufficient data, fetch the data from scratch
            logger.info("Missing data in DB, fetching from data sources...")
            self.fetch_process_store_data(**kwargs)
            # Fetch data from database again
            logger.info("Fetching data from DB again...")
            self.fetch_data_from_database(**kwargs)
            # Check data validity again. If there is an error here, it means there is an
            # integrity error because of some changes on Blizzard side, and the API
            # needs to be updated to properly work again
            self.check_data_integrity()

        # Update API Cache once we know we have valid data to return
        self.cache_manager.update_api_cache(self.cache_key, self.data, self.timeout)

        logger.info("Done ! Returning data...")
        return self.data

    def check_data_integrity(self) -> None:
        """This method will just try to instanciate Pydantic object, and
        will raise a ValidationError in case there is an issue
        """
        [self.response_model(**res) for res in self.data]
        if isinstance(self.data, list)
        else self.response_model(**self.data)

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
