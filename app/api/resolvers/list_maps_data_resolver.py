"""List Maps Request Handler module"""

from typing import ClassVar

from app.config import settings
from app.parsers.maps_parser import MapsParser

from .base_data_resolver import BaseDataResolver


class ListMapsDataResolver(BaseDataResolver):
    """List Maps Request Handler used in order to retrieve a list of
    available Overwatch maps, using the MapsParser class.
    """

    parser_classes: ClassVar[list] = [MapsParser]
    timeout = settings.csv_cache_timeout
