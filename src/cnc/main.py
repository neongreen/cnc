# How to run: see mise.toml
# How to add dependencies: `uv add <dependency>`

from pathlib import Path
from flask import Flask, send_from_directory
import shutil
import glob

from cnc.hive import generate_hive_html, load_hive_data
from cnc.maturity import (
    generate_maturity_html,
    load_maturity_data,
    load_maturity_players,
)


root = Path(__file__).parent.parent.parent


app = Flask(__name__, template_folder=root / "templates", static_folder=None)


@app.route("/")
def serve_html():
    return send_from_directory(root / "build", "index.html")


@app.route("/hive")
def serve_hive():
    return send_from_directory(root / "build", "hive.html")


@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory(root / "build", filename)


# Build
with app.app_context():
    output_dir = root / "build"
    output_dir.mkdir(exist_ok=True)

    # maturity matches
    maturity = load_maturity_data(root / "data" / "maturity.csv")
    maturity_inactive = load_maturity_players(root / "data" / "maturity-players.toml")

    maturity_output_path = output_dir / "index.html"
    open(maturity_output_path, "w").write(
        generate_maturity_html(maturity, inactive_players=maturity_inactive)
    )
    print(f"Generated maturity HTML at {maturity_output_path}")

    # hive
    hive = load_hive_data(root / "data" / "hive.toml")
    hive_output_path = output_dir / "hive.html"
    open(hive_output_path, "w").write(generate_hive_html(hive))
    print(f"Generated hive HTML at {hive_output_path}")

    # everything else
    shutil.copyfile("graph.js", output_dir / "graph.js")
    shutil.rmtree(output_dir / "static", ignore_errors=True)
    shutil.copytree("static", output_dir / "static")


def dev():
    """Run the development server with live reloading."""

    extra_files = []
    # TODO: this doesnt seem to reload the templates
    extra_files += glob.glob(
        "{templates,data,static}/**/*.*", root_dir=root, recursive=True
    )
    extra_files += glob.glob("src/**/*.py", root_dir=root, recursive=True)
    extra_files += glob.glob("graph.js", root_dir=root)

    app.run(debug=True, host="0.0.0.0", port=5500, extra_files=extra_files)


def build():
    """Build the static site."""

    # Do nothing, the build is done in the main script
    pass
