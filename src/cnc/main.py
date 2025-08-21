# Copyright (c) 2025 Emily
#
# This work is licensed under the Creative Commons Zero v1.0 Universal License.
#
# To the extent possible under law, the author(s) have dedicated all copyright and related or neighboring rights to this software to the public domain worldwide. This software is distributed without any warranty.
#
# You should have received a copy of the CC0 Public Domain Dedication along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

# How to run: see mise.toml
# How to add dependencies: `uv add <dependency>`

from pathlib import Path
from flask import Flask, send_from_directory
import shutil

import structlog

from cnc.utils import setup_logging
from cnc.hive.html_generator import generate_hive_html
from cnc.maturity import (
    generate_maturity_html,
    load_maturity_data,
    load_maturity_players,
)

logger = structlog.get_logger()

setup_logging()

root = Path(__file__).parent.parent.parent


app = Flask(__name__, template_folder=root / "templates", static_folder=None)


def build():
    """Build the static site."""

    with app.app_context():
        logger.info("Starting build process")
        output_dir = root / "build"
        output_dir.mkdir(exist_ok=True)
        logger.debug(f"Output directory: {output_dir}")

        # maturity matches
        logger.info("Generating maturity HTML")
        maturity = load_maturity_data(root / "data" / "maturity.csv")
        maturity_inactive = load_maturity_players(
            root / "data" / "maturity-players.toml"
        )

        maturity_output_path = output_dir / "index.html"
        open(maturity_output_path, "w").write(
            generate_maturity_html(maturity, inactive_players=maturity_inactive)
        )
        logger.info(f"Generated maturity HTML at {maturity_output_path}")

        # hive
        logger.info("Generating hive HTML")
        hive_output_path = output_dir / "hive.html"
        open(hive_output_path, "w").write(generate_hive_html())
        logger.info(f"Generated hive HTML at {hive_output_path}")

        # everything else
        logger.info("Copying static files")
        shutil.copyfile("graph.js", output_dir / "graph.js")
        shutil.rmtree(output_dir / "static", ignore_errors=True)
        shutil.copytree("static", output_dir / "static")
        logger.info("Build process completed successfully")


@app.route("/")
def serve_html():
    return send_from_directory(root / "build", "index.html")


@app.route("/hive")
def serve_hive():
    return send_from_directory(root / "build", "hive.html")


@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory(root / "build", filename)


def build_and_exit():
    build()
    exit(0)
