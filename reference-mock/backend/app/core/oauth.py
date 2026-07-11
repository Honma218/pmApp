"""Google OAuth 2.0 / OIDC クライアント（Authlib）。

state / nonce / PKCE / id_token 検証は Authlib に委ねる。具体的なプロバイダ依存は
ここに閉じ込め、ドメイン層（services）からは呼ばない。
"""

from authlib.integrations.starlette_client import OAuth

from app.core.config import get_settings

_settings = get_settings()

oauth = OAuth()
oauth.register(
    name="google",
    client_id=_settings.GOOGLE_OAUTH_CLIENT_ID,
    client_secret=_settings.GOOGLE_OAUTH_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)
