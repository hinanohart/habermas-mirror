"""Console-script entrypoint: `habermas-mirror`."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="habermas-mirror",
        description="Self-hostable Habermas Machine reference re-implementation.",
    )
    sub = parser.add_subparsers(dest="cmd")

    serve = sub.add_parser("serve", help="Run the FastAPI server (uvicorn).")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")

    sub.add_parser("version", help="Print the package version.")

    args = parser.parse_args(argv)

    if args.cmd == "serve":
        import uvicorn

        uvicorn.run(
            "habermas_mirror.main:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
        )
        return 0

    if args.cmd == "version":
        from habermas_mirror import __version__

        print(__version__)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
