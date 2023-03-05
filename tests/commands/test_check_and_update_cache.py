import asyncio
from unittest.mock import Mock, patch

import pytest
from httpx import TimeoutException

from app.commands.check_and_update_cache import get_soon_expired_cache_keys
from app.commands.check_and_update_cache import main as check_and_update_cache_main
from app.common.cache_manager import CacheManager
from app.common.enums import Locale
from app.common.helpers import overfast_client
from app.config import settings


@pytest.fixture()
def cache_manager():
    return CacheManager()


@pytest.fixture()
def locale():
    return Locale.ENGLISH_US


def test_check_and_update_gamemodes_cache_to_update(
    cache_manager: CacheManager,
    locale: str,
    home_html_data: list,
    gamemodes_json_data: dict,
):
    gamemodes_cache_key = (
        f"GamemodesParser-{settings.blizzard_host}/{locale}{settings.home_path}"
    )
    complete_cache_key = f"{settings.parser_cache_key_prefix}:{gamemodes_cache_key}"

    # Add some data (to update and not to update)
    cache_manager.update_parser_cache(
        f"PlayerParser-{settings.blizzard_host}/{locale}{settings.career_path}/TeKrop-2217",
        {},
        settings.expired_cache_refresh_limit + 30,
    )
    cache_manager.update_parser_cache(
        f"HeroParser-{settings.blizzard_host}/{locale}{settings.heroes_path}/ana",
        {},
        settings.expired_cache_refresh_limit + 5,
    )
    cache_manager.update_parser_cache(
        gamemodes_cache_key, [], settings.expired_cache_refresh_limit - 5
    )

    assert get_soon_expired_cache_keys() == {complete_cache_key}

    # check and update (only gamemodes should be updated)
    logger_info_mock = Mock()
    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(status_code=200, text=home_html_data),
    ), patch("app.common.logging.logger.info", logger_info_mock):
        asyncio.run(check_and_update_cache_main())

    # Check data in db (assert we created API Cache for subroutes)
    logger_info_mock.assert_any_call("Done ! Retrieved keys : {}", 1)
    logger_info_mock.assert_any_call("Updating data for {} key...", complete_cache_key)

    assert cache_manager.get_parser_cache(gamemodes_cache_key) == gamemodes_json_data


@pytest.mark.parametrize(
    ("hero_html_data", "hero_json_data"),
    [("ana", "ana")],
    indirect=["hero_html_data", "hero_json_data"],
)
def test_check_and_update_specific_hero_to_update(
    cache_manager: CacheManager, locale: str, hero_html_data: str, hero_json_data: dict
):
    ana_cache_key = (
        f"HeroParser-{settings.blizzard_host}/{locale}{settings.heroes_path}/ana"
    )
    complete_cache_key = f"{settings.parser_cache_key_prefix}:{ana_cache_key}"

    # Add some data (to update and not to update)
    cache_manager.update_parser_cache(
        ana_cache_key, {}, settings.expired_cache_refresh_limit - 5
    )

    # Check data in db (assert no Parser Cache data)
    assert cache_manager.get_parser_cache(ana_cache_key) == {}
    assert get_soon_expired_cache_keys() == {complete_cache_key}

    # check and update (only maps should be updated)
    logger_info_mock = Mock()
    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(status_code=200, text=hero_html_data),
    ), patch("app.common.logging.logger.info", logger_info_mock):
        asyncio.run(check_and_update_cache_main())

    # Check data in db (assert we created API Cache for subroutes)
    logger_info_mock.assert_any_call("Done ! Retrieved keys : {}", 1)
    logger_info_mock.assert_any_call("Updating data for {} key...", complete_cache_key)

    # Remove portrait as this is retrieved from heroes list
    hero_data = hero_json_data.copy()
    del hero_data["portrait"]

    assert cache_manager.get_parser_cache(ana_cache_key) == hero_data


def test_check_and_update_maps_to_update(
    cache_manager: CacheManager, maps_json_data: dict
):
    cache_key = "MapsParser"
    complete_cache_key = f"{settings.parser_cache_key_prefix}:{cache_key}"

    # Add some data (to update and not to update)
    cache_manager.update_parser_cache(
        cache_key, [], settings.expired_cache_refresh_limit - 5
    )

    # Check data in db (assert no Parser Cache data)
    assert cache_manager.get_parser_cache(cache_key) == []
    assert get_soon_expired_cache_keys() == {complete_cache_key}

    # check and update (only maps should be updated)
    logger_info_mock = Mock()

    with patch("app.common.logging.logger.info", logger_info_mock):
        asyncio.run(check_and_update_cache_main())

    # Check data in db (assert we created API Cache for subroutes)
    logger_info_mock.assert_any_call("Done ! Retrieved keys : {}", 1)
    logger_info_mock.assert_any_call("Updating data for {} key...", complete_cache_key)

    assert cache_manager.get_parser_cache(cache_key) == maps_json_data


def test_check_and_update_cache_no_update(cache_manager: CacheManager, locale: str):
    # Add some data (to update and not to update)
    cache_manager.update_parser_cache(
        f"PlayerParser-{settings.blizzard_host}/{locale}{settings.career_path}/TeKrop-2217",
        {},
        settings.expired_cache_refresh_limit + 30,
    )
    cache_manager.update_parser_cache(
        f"HeroParser-{settings.blizzard_host}/{locale}{settings.heroes_path}/ana",
        {},
        settings.expired_cache_refresh_limit + 5,
    )
    cache_manager.update_parser_cache(
        f"GamemodesParser-{settings.blizzard_host}/{locale}{settings.home_path}",
        [],
        settings.expired_cache_refresh_limit + 10,
    )

    assert get_soon_expired_cache_keys() == set()

    # check and update (no update)
    logger_info_mock = Mock()
    with patch("app.common.logging.logger.info", logger_info_mock):
        asyncio.run(check_and_update_cache_main())

    logger_info_mock.assert_any_call("Done ! Retrieved keys : {}", 0)


@pytest.mark.parametrize(
    ("player_html_data", "player_json_data"),
    [("TeKrop-2217", "TeKrop-2217")],
    indirect=["player_html_data", "player_json_data"],
)
def test_check_and_update_specific_player_to_update(
    cache_manager: CacheManager,
    locale: str,
    player_html_data: str,
    player_json_data: dict,
):
    player_cache_key = f"PlayerParser-{settings.blizzard_host}/{locale}{settings.career_path}/TeKrop-2217/"
    complete_cache_key = f"{settings.parser_cache_key_prefix}:{player_cache_key}"

    # Add some data (to update and not to update)
    cache_manager.update_parser_cache(
        player_cache_key, {}, settings.expired_cache_refresh_limit - 5
    )
    cache_manager.update_parser_cache(
        f"HeroParser-{settings.blizzard_host}/{locale}{settings.heroes_path}/ana",
        {},
        settings.expired_cache_refresh_limit + 5,
    )
    cache_manager.update_parser_cache(
        f"GamemodesParser-{settings.blizzard_host}/{locale}{settings.home_path}",
        [],
        settings.expired_cache_refresh_limit + 10,
    )

    # Check data in db (assert no Parser Cache data)
    assert cache_manager.get_parser_cache(player_cache_key) == {}
    assert get_soon_expired_cache_keys() == {complete_cache_key}

    # check and update (only maps should be updated)
    logger_info_mock = Mock()
    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(
            status_code=200,
            text=player_html_data,
        ),
    ), patch("app.common.logging.logger.info", logger_info_mock):
        asyncio.run(check_and_update_cache_main())

    # Check data in db (assert we created API Cache for subroutes)
    logger_info_mock.assert_any_call("Done ! Retrieved keys : {}", 1)
    logger_info_mock.assert_any_call("Updating data for {} key...", complete_cache_key)

    assert cache_manager.get_parser_cache(player_cache_key) == player_json_data


@pytest.mark.parametrize(
    ("player_html_data", "player_stats_json_data"),
    [("TeKrop-2217", "TeKrop-2217")],
    indirect=["player_html_data", "player_stats_json_data"],
)
def test_check_and_update_player_stats_summary_to_update(
    cache_manager: CacheManager,
    locale: str,
    player_html_data: str,
    player_stats_json_data: dict,
):
    player_stats_cache_key = f"PlayerStatsSummaryParser-{settings.blizzard_host}/{locale}{settings.career_path}/TeKrop-2217/"
    complete_cache_key = f"{settings.parser_cache_key_prefix}:{player_stats_cache_key}"

    # Add some data (to update and not to update)
    cache_manager.update_parser_cache(
        player_stats_cache_key, {}, settings.expired_cache_refresh_limit - 5
    )
    cache_manager.update_parser_cache(
        f"HeroParser-{settings.blizzard_host}/{locale}{settings.heroes_path}/ana",
        {},
        settings.expired_cache_refresh_limit + 5,
    )
    cache_manager.update_parser_cache(
        f"GamemodesParser-{settings.blizzard_host}/{locale}{settings.home_path}",
        [],
        settings.expired_cache_refresh_limit + 10,
    )

    # Check data in db (assert no Parser Cache data)
    assert cache_manager.get_parser_cache(player_stats_cache_key) == {}
    assert get_soon_expired_cache_keys() == {complete_cache_key}

    # check and update (only maps should be updated)
    logger_info_mock = Mock()
    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(
            status_code=200,
            text=player_html_data,
        ),
    ), patch("app.common.logging.logger.info", logger_info_mock):
        asyncio.run(check_and_update_cache_main())

    # Check data in db (assert we created API Cache for subroutes)
    logger_info_mock.assert_any_call("Done ! Retrieved keys : {}", 1)
    logger_info_mock.assert_any_call("Updating data for {} key...", complete_cache_key)

    assert (
        cache_manager.get_parser_cache(player_stats_cache_key) == player_stats_json_data
    )


def test_check_internal_error_from_blizzard(cache_manager: CacheManager, locale: str):
    # Add some data (to update and not to update)
    cache_manager.update_parser_cache(
        f"HeroParser-{settings.blizzard_host}/{locale}{settings.heroes_path}/ana",
        {},
        settings.expired_cache_refresh_limit - 5,
    )

    logger_error_mock = Mock()
    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(status_code=500, text="Internal Server Error"),
    ), patch("app.common.logging.logger.error", logger_error_mock):
        asyncio.run(check_and_update_cache_main())

    logger_error_mock.assert_any_call(
        "Received an error from Blizzard. HTTP {} : {}", 500, "Internal Server Error"
    )


def test_check_timeout_from_blizzard(cache_manager: CacheManager, locale: str):
    # Add some data (to update and not to update)
    cache_manager.update_parser_cache(
        f"HeroParser-{settings.blizzard_host}/{locale}{settings.heroes_path}/ana",
        {},
        settings.expired_cache_refresh_limit - 5,
    )

    logger_error_mock = Mock()
    with patch.object(
        overfast_client,
        "get",
        side_effect=TimeoutException(
            "HTTPSConnectionPool(host='overwatch.blizzard.com', port=443): "
            "Read timed out. (read timeout=10)"
        ),
    ), patch("app.common.logging.logger.error", logger_error_mock):
        asyncio.run(check_and_update_cache_main())

    logger_error_mock.assert_any_call(
        "Received an error from Blizzard. HTTP {} : {}",
        0,
        "Blizzard took more than 10 seconds to respond, resulting in a timeout",
    )


@pytest.mark.parametrize("player_html_data", ["TeKrop-2217"], indirect=True)
def test_check_parser_parsing_error(
    cache_manager: CacheManager, locale: str, player_html_data: str
):
    # Add some data (to update and not to update)
    cache_manager.update_parser_cache(
        f"PlayerParser-{settings.blizzard_host}/{locale}{settings.career_path}/TeKrop-2217",
        {},
        settings.expired_cache_refresh_limit - 5,
    )

    logger_critical_mock = Mock()

    player_attr_error = player_html_data.replace(
        'class="Profile-player--summaryWrapper"', 'class="blabla"'
    )
    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(status_code=200, text=player_attr_error),
    ), patch("app.common.logging.logger.critical", logger_critical_mock):
        asyncio.run(check_and_update_cache_main())

    logger_critical_mock.assert_called_with(
        "Internal server error for URL {} : {}",
        "https://overwatch.blizzard.com/en-us/career/TeKrop-2217/",
        "AttributeError(\"'NoneType' object has no attribute 'find'\")",
    )


@pytest.mark.parametrize("player_html_data", ["Unknown-1234"], indirect=True)
def test_check_parser_init_error(
    cache_manager: CacheManager, locale: str, player_html_data: str
):
    # Add some data (to update and not to update)
    cache_manager.update_parser_cache(
        f"PlayerParser-{settings.blizzard_host}/{locale}{settings.career_path}/TeKrop-2217",
        {},
        settings.expired_cache_refresh_limit - 5,
    )

    logger_exception_mock = Mock()
    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(status_code=200, text=player_html_data),
    ), patch("app.common.logging.logger.exception", logger_exception_mock):
        asyncio.run(check_and_update_cache_main())

    logger_exception_mock.assert_any_call(
        "Failed to instanciate Parser when refreshing : {}", "Player not found"
    )


def test_check_and_update_several_to_update(
    cache_manager: CacheManager,
    locale: str,
    home_html_data: list,
    gamemodes_json_data: dict,
    maps_json_data: dict,
):
    gamemodes_cache_key = (
        f"GamemodesParser-{settings.blizzard_host}/{locale}{settings.home_path}"
    )
    maps_cache_key = "MapsParser"

    complete_gamemodes_cache_key = (
        f"{settings.parser_cache_key_prefix}:{gamemodes_cache_key}"
    )
    complete_map_cache_key = f"{settings.parser_cache_key_prefix}:{maps_cache_key}"

    # Add some data to update
    cache_manager.update_parser_cache(
        gamemodes_cache_key, [], settings.expired_cache_refresh_limit - 5
    )
    cache_manager.update_parser_cache(
        maps_cache_key, [], settings.expired_cache_refresh_limit - 5
    )

    assert get_soon_expired_cache_keys() == {
        complete_gamemodes_cache_key,
        complete_map_cache_key,
    }

    # check and update (only gamemodes should be updated)
    logger_info_mock = Mock()
    with patch.object(
        overfast_client,
        "get",
        return_value=Mock(status_code=200, text=home_html_data),
    ), patch("app.common.logging.logger.info", logger_info_mock):
        asyncio.run(check_and_update_cache_main())

    # Check data in db (assert we created API Cache for subroutes)
    logger_info_mock.assert_any_call("Done ! Retrieved keys : {}", 2)
    logger_info_mock.assert_any_call(
        "Updating data for {} key...", complete_gamemodes_cache_key
    )
    logger_info_mock.assert_any_call(
        "Updating data for {} key...", complete_map_cache_key
    )

    assert cache_manager.get_parser_cache(gamemodes_cache_key) == gamemodes_json_data
    assert cache_manager.get_parser_cache(maps_cache_key) == maps_json_data
