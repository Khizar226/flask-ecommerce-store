"""Entry point: `flask --app app run` or `python app.py` for local development."""

import os

from dotenv import load_dotenv

load_dotenv()

from shop import create_app  # noqa: E402  (env must load before config is read)

app = create_app()

if __name__ == "__main__":
    # Debug mode exposes an interactive console; never enable it in production.
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
