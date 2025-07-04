# pyright: reportUnusedFunction=false, reportMissingTypeStubs=false

import asyncio
import os
import secrets
import threading
from typing import Any

from authlib.integrations.flask_client import OAuth
from discord.ext import commands
from flask import Flask, redirect, request, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.serving import BaseWSGIServer, make_server

from web.oauth import OAuthManager

BASE_HTML = """
<!doctype html>
<html lang="en">

<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Verification {status}</title>
</head>

<body>
    <p>{message}</p>
</body>

</html>
"""


class OAuthServer:
    def __init__(
        self, bot: commands.Bot, oauth_manager: OAuthManager, port: int = 8080
    ):
        self.bot: commands.Bot = bot
        self.oauth_manager: OAuthManager = oauth_manager

        self.app: Flask = Flask(__name__)
        self.app.wsgi_app = ProxyFix(self.app.wsgi_app, x_proto=1, x_host=1)
        self.app.secret_key = os.getenv("FLASK_SECRET_KEY", secrets.token_urlsafe(32))

        self.port: int = port
        self.base_url: str = os.getenv("OAUTH_BASE_URL", f"http://localhost:{port}")

        # setup OAuth
        self.oauth: OAuth = OAuth(self.app)
        self.google: Any = self.oauth.register(  # pyright: ignore[reportExplicitAny, reportUnknownMemberType]
            name="google",
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email"},
        )

        # setup routes
        self.setup_routes()
        self.server: BaseWSGIServer | None = None
        self.server_thread: threading.Thread | None = None

    def setup_routes(self):
        @self.app.route("/")
        def home():
            return redirect("https://discord.gg/UmmbZ8qPbV")

        @self.app.route("/health")
        def health():
            return {"status": "ok"}

        @self.app.route("/oauth/login/<int:user_id>")
        def oauth_login(user_id: int):
            # store user_id in Redis using a generated state token
            state_future = asyncio.run_coroutine_threadsafe(
                self.oauth_manager.create_verification_session(user_id),
                self.bot.loop,
            )

            try:
                state = state_future.result(timeout=5)
            except TimeoutError:
                return self.error_page("Internal timeout during login setup.")

            redirect_uri = url_for("oauth_callback", _external=True)
            return self.google.authorize_redirect(redirect_uri, state=state)

        @self.app.route("/oauth/callback")
        def oauth_callback():
            try:
                # get user_id from Redis using state token from OAuth response
                state = request.args.get("state")
                if not state:
                    return self.error_page("Invalid or missing OAuth state.")

                user_id_future = asyncio.run_coroutine_threadsafe(
                    self.oauth_manager.get_user_from_state(state), self.bot.loop
                )
                user_id = user_id_future.result()

                # delete state token to prevent replay attacks
                asyncio.run_coroutine_threadsafe(
                    self.oauth_manager.delete_verification_session(state),
                    self.bot.loop,
                )

                if user_id is None:
                    return self.error_page("Invalid or expired verification session.")

                # exchange code for token
                token = self.google.authorize_access_token()
                user_info = token.get("userinfo")

                if not user_info:
                    return self.error_page("Failed to get user information.")

                email = user_info.get("email", "").lower()

                # verify it's a CMU email
                if not email.endswith("cmu.edu"):
                    return self.error_page("You must use a CMU email address.")

                andrewid = email.split("@")[0]

                # check if the andrewid is banned
                is_banned_future = asyncio.run_coroutine_threadsafe(
                    self.oauth_manager.is_banned(andrewid), self.bot.loop
                )
                is_banned = is_banned_future.result()

                if is_banned:
                    ban_reason_future = asyncio.run_coroutine_threadsafe(
                        self.oauth_manager.get_ban_reason(andrewid), self.bot.loop
                    )
                    ban_reason = ban_reason_future.result()

                    asyncio.run_coroutine_threadsafe(
                        self.oauth_manager.enforce_ban(
                            self.bot,
                            user_id,
                            andrewid,
                            ban_reason or "No reason provided",
                        ),
                        self.bot.loop,
                    )

                    return self.error_page("You are banned from this server.")

                # check if andrewid is already linked to another account
                existing_user_future = asyncio.run_coroutine_threadsafe(
                    self.oauth_manager.get_user_by_andrewid(andrewid), self.bot.loop
                )
                existing_user = existing_user_future.result()

                if existing_user and existing_user != user_id:
                    return self.error_page(
                        "This CMU email is already linked to another Discord account."
                    )

                # store the andrewid
                asyncio.run_coroutine_threadsafe(
                    self.oauth_manager.store_andrewid(user_id, andrewid),
                    self.bot.loop,
                )

                # complete verification in Discord
                asyncio.run_coroutine_threadsafe(
                    self.oauth_manager.complete_verification(
                        self.bot, user_id, andrewid
                    ),
                    self.bot.loop,
                )

                return self.success_page(andrewid)

            except Exception as e:
                print(f"OAuth callback error: {e}")
                return self.error_page(
                    "An unexpected error occurred during verification."
                )

    def success_page(self, andrewid: str):
        return BASE_HTML.format(
            status="Complete",
            message=f"Successfully verified {andrewid}. You may now close this tab and return to Discord.",
        )

    def error_page(self, message: str):
        return BASE_HTML.format(status="Error", message=message)

    def start_server(self, host: str = "0.0.0.0"):
        # start the OAuth server in a separate thread
        def run_server():
            self.server = make_server(host, self.port, self.app, threaded=True)
            print(f"OAuth server started on http://{host}:{self.port}")
            self.server.serve_forever()

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()

    def stop_server(self):
        if self.server:
            self.server.shutdown()
            print("OAuth server stopped")

    def get_verification_url(self, user_id: int) -> str:
        return f"{self.base_url}/oauth/login/{user_id}"
