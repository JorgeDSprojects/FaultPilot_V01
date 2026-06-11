from __future__ import annotations

import os

from faultpilot.ui.app import SERVER_PORT_ATTR, THEME_ATTR, create_app
from faultpilot.ui.settings import DEFAULT_SERVER_PORT


demo = create_app()


if __name__ == "__main__":
    configured_port = int(getattr(demo, SERVER_PORT_ATTR, DEFAULT_SERVER_PORT))
    server_port = int(os.getenv("PORT", str(configured_port)))
    theme = getattr(demo, THEME_ATTR, None)
    demo.launch(server_name="0.0.0.0", server_port=server_port, theme=theme)
