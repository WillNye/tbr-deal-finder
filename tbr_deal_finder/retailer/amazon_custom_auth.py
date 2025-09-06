import logging
from typing import Optional, Any, Union
from urllib.parse import parse_qs

import audible
import httpx
from audible.login import create_code_verifier, build_oauth_url
from audible.register import register as register_

logger = logging.getLogger(__name__)


def external_login(
        response_url: str,
        domain: str,
        serial: str,
        code_verifier: bytes,
) -> dict[str, Any]:
    response_url = httpx.URL(response_url)
    parsed_url = parse_qs(response_url.query.decode())

    authorization_code = parsed_url["openid.oa2.authorization_code"][0]

    return {
        "authorization_code": authorization_code,
        "code_verifier": code_verifier,
        "domain": domain,
        "serial": serial
    }


class CustomAuthenticator(audible.Authenticator):
    _with_username: Optional[bool] = False
    _serial: Optional[str] = None
    _code_verifier: Optional[bytes] = None
    oauth_url: Optional[str] = None

    @classmethod
    def from_locale(
        cls,
        locale: Union[str, "Locale"],
        serial: Optional[str] = None,
        with_username: bool = False,
    ):
        auth = cls()
        auth.locale = locale
        auth._with_username = with_username
        auth._code_verifier = create_code_verifier()
        auth.oauth_url, auth._serial = build_oauth_url(
            country_code=auth.locale.country_code,
            domain=auth.locale.domain,
            market_place_id=auth.locale.market_place_id,
            code_verifier=auth._code_verifier,
            serial=serial,
            with_username=with_username
        )

        return auth

    def external_login(self, response_url: str):

        login_device = external_login(
                response_url,
                self.locale.domain,
                self._serial,
                self._code_verifier
        )
        logger.info("logged in to Audible.")

        register_device = register_(
            with_username=self._with_username,
            **login_device
        )

        self._update_attrs(
            with_username=self._with_username,
            **register_device
        )
        logger.info("registered Audible device")
