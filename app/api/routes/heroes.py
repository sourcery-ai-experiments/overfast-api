"""Heroes endpoints router : heroes list, heroes details, etc."""

from fastapi import APIRouter, Path, Query, Request, status

from app.api.resolvers.list_heroes_data_resolver import ListHeroesDataResolver
from app.handlers.get_hero_request_handler import GetHeroDataResolver
from app.models.errors import HeroParserErrorMessage
from app.models.heroes import Hero, HeroShort
from app.utils.decorators import validation_error_handler
from app.utils.enums import HeroKey, Locale, Role, RouteTag
from app.utils.helpers import routes_responses

router = APIRouter()


@router.get(
    "",
    responses=routes_responses,
    tags=[RouteTag.HEROES],
    summary="Get a list of heroes",
    description=(
        "Get a list of Overwatch heroes, which can be filtered using roles. "
        "<br />**Cache TTL : 1 day.**"
    ),
    operation_id="list_heroes",
)
@validation_error_handler(response_model=HeroShort)
async def list_heroes(
    request: Request,
    role: Role = Query(None, title="Role filter"),
    locale: Locale = Query(Locale.ENGLISH_US, title="Locale to be displayed"),
) -> list[HeroShort]:
    return await ListHeroesDataResolver(
        request=request,
        response_model=HeroShort,
    ).process_query(
        role=role,
        locale=locale,
    )


@router.get(
    "/{hero_key}",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": HeroParserErrorMessage,
            "description": "Hero Not Found",
        },
        **routes_responses,
    },
    tags=[RouteTag.HEROES],
    summary="Get hero data",
    description=(
        "Get data about an Overwatch hero : description, abilities, story, etc. "
        "<br />**Cache TTL : 1 day.**"
    ),
    operation_id="get_hero",
)
@validation_error_handler(response_model=Hero)
async def get_hero(
    request: Request,
    hero_key: HeroKey = Path(title="Key name of the hero"),
    locale: Locale = Query(Locale.ENGLISH_US, title="Locale to be displayed"),
) -> Hero:
    return await GetHeroDataResolver(
        request=request,
        response_model=Hero,
    ).process_query(
        hero_key=hero_key,
        locale=locale,
    )
