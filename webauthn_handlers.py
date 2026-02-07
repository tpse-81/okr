from dataclasses import dataclass
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    AuthenticatorAttachment,
    ResidentKeyRequirement,
)
import uuid
from json import dumps
from litestar.exceptions import ClientException
from webauthn.helpers.exceptions import (
    InvalidRegistrationResponse,
    InvalidAuthenticationResponse,
)
from litestar.params import Body, Parameter
from typing import cast, Any
from webauthn.registration.generate_registration_options import (
    generate_registration_options,
)
from webauthn.authentication.generate_authentication_options import (
    generate_authentication_options,
)
from webauthn.registration.verify_registration_response import (
    verify_registration_response,
)
from webauthn.authentication.verify_authentication_response import (
    verify_authentication_response,
)
from webauthn.helpers import (
    options_to_json_dict,
    base64url_to_bytes,
    bytes_to_base64url,
)
from sqlalchemy.ext.asyncio import AsyncSession
from litestar import post, Request, delete, get

from config import config
from models.user import User
from models.webauthn_credentials import WebauthnCredentials

# possible TODO: challenges could be stored in the database
# however, since Python dicts are thread-safe and webauthn challenges expire
# within few minutes, it's probably not worth it
registration_challenges: dict[uuid.UUID, str] = {}
auth_challenges: dict[str, str] = {}

# see https://webauthn.guide/ for reference


@post("/webauthn/registration_options")
async def webauthn_get_registration_options(
    db_session: AsyncSession, request: Request
) -> dict[str, Any]:
    """
    Get the server's Webauthn registration options.

    param user_id: the ID of the user to authenticate
    return: the Webauthn registration options
    """
    user = cast(User, request.user)
    opts = generate_registration_options(
        rp_id=config.twofa_config.app_url,
        rp_name=config.twofa_config.app_name,
        user_name=user.name,
        # selecting an authenticator is required in order for authenticator
        # apps to discover/suggest the passkey - see https://web.dev/articles/webauthn-discoverable-credentials
        authenticator_selection=AuthenticatorSelectionCriteria(
            authenticator_attachment=AuthenticatorAttachment.PLATFORM,
            resident_key=ResidentKeyRequirement.REQUIRED,
            require_resident_key=True,
        ),
    )
    registration_challenges[user.id] = bytes_to_base64url(opts.challenge)
    return options_to_json_dict(opts)


@post("/webauthn/register")
async def webauthn_register(
    db_session: AsyncSession,
    request: Request,
    data: dict[str, Any] = Body(description="Webauthn registration response"),
) -> None:
    """
    Attempt to register the given Webauthn credentials for the user.

    param data: the webauthn registration response
    """
    user = cast(User, request.user)

    try:
        verified_registration = verify_registration_response(
            credential=data,
            expected_challenge=base64url_to_bytes(registration_challenges[user.id]),
            expected_rp_id=config.twofa_config.app_url,
            expected_origin=config.cors_allow_origins,
        )
    except InvalidRegistrationResponse as e:
        raise ClientException(e)

    credentials = WebauthnCredentials(
        credential_id=bytes_to_base64url(verified_registration.credential_id),
        credential_public_key=bytes_to_base64url(
            verified_registration.credential_public_key
        ),
        sign_count=verified_registration.sign_count,
        credential_device_type=verified_registration.credential_device_type,
        credential_backed_up=verified_registration.credential_backed_up,
        credential_transports=dumps(data["response"]["transports"]),
    )
    # link credentials to current user
    credentials.user_id = user.id

    db_session.add(credentials)
    await db_session.commit()


async def _get_user_credentials(
    db_session: AsyncSession, user_id: str
) -> WebauthnCredentials:
    user = await db_session.get(User, user_id)
    if not user:
        raise ClientException("user does not exist")

    if not user.webauthn:
        raise ClientException("no webauthn configured")

    return user.webauthn


@post("/webauthn/authentication_options/{user_id:str}")
async def webauthn_get_authentication_options(
    db_session: AsyncSession,
    user_id: str = Parameter(),
) -> dict[str, Any]:
    """
    Get the server's Webauthn authentication options.

    param user_id: the ID of the user to authenticate
    return: the Webauthn authentication options
    """
    # verify that webauthn is properly set up
    _ = await _get_user_credentials(db_session, user_id)

    auth_options = generate_authentication_options(
        rp_id=config.twofa_config.app_url,
    )
    auth_challenges[user_id] = bytes_to_base64url(auth_options.challenge)

    return options_to_json_dict(auth_options)


def try_authenticate_user(
    user_id: str,
    webauthn_credentials: WebauthnCredentials,
    authentication_response: dict[str, Any],
):
    try:
        verify_authentication_response(
            credential=authentication_response,
            expected_challenge=base64url_to_bytes(auth_challenges[user_id]),
            expected_rp_id=config.twofa_config.app_url,
            expected_origin=config.cors_allow_origins,
            credential_public_key=base64url_to_bytes(
                webauthn_credentials.credential_public_key
            ),
            credential_current_sign_count=webauthn_credentials.sign_count,
        )
    except InvalidAuthenticationResponse as e:
        raise ClientException(e)


@post("/webauthn/authenticate/{user_id:str}")
async def webauthn_authenticate(
    db_session: AsyncSession,
    user_id: str = Parameter(),
    data: dict[str, Any] = Body(description="Webauthn authentication response"),
) -> None:
    """
    Attempt to authenticate the user with the given Webauthn credentials.

    param user_id: the ID of the user to authenticate
    param data: the webauthn authentication response
    """
    webauthn_credentials = await _get_user_credentials(db_session, user_id)

    try_authenticate_user(user_id, webauthn_credentials, data)


@delete("/webauthn/remove_credentials/{user_id:str}")
async def webauthn_remove_credentials(
    db_session: AsyncSession,
    user_id: str = Parameter(),
    data: dict[str, Any] = Body(description="Webauthn authentication response"),
) -> None:
    """
    Delete the Webauthn credentials stored for the current user.
    This requires to go through the full login flow first to validate that the current user still has access to the passkey and is hence allowed to remove it.

    param user_id: the ID of the user to authenticate
    param data: the webauthn authentication response
    """
    webauthn_credentials = await _get_user_credentials(db_session, user_id)

    # confirm that the user has access to the credentials
    # otherwise, they're not allowed to delete their account
    try_authenticate_user(user_id, webauthn_credentials, data)

    await db_session.delete(webauthn_credentials)
    await db_session.commit()


@dataclass
class WebauthnConfiguredResponse:
    is_configured: bool


@get("/webauthn/is_configured")
async def webauthn_is_configured(
    db_session: AsyncSession, request: Request
) -> WebauthnConfiguredResponse:
    """
    Check whether Webauthn is configured for the logged-in user.

    return: whether the account has set up Webauthn
    """
    user = cast(User, request.user)

    return WebauthnConfiguredResponse(is_configured=user.webauthn is not None)
