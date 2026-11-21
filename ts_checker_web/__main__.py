"""Entry point: python -m ts_checker_web --data-dir <path> --port <port> [--checker <path>]"""

import argparse
import sys

from .server import create_server


def _port(value):
    try:
        port = int(value, 10)
    except ValueError:
        raise argparse.ArgumentTypeError("port must be an integer 0..65535")
    if not 0 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be an integer 0..65535")
    return port


def _build_parser():
    parser = argparse.ArgumentParser(
        prog="python -m ts_checker_web",
        description="Local web UI for the ts_subset_check checker (binds 127.0.0.1 only).",
        allow_abbrev=False,
    )
    parser.add_argument("--data-dir", required=True, help="directory reserved for saved documents (created if missing)")
    parser.add_argument("--port", required=True, type=_port, help="TCP port on 127.0.0.1 (0 = ephemeral)")
    parser.add_argument("--checker", default=None, help="path to the ts_subset_check binary")
    return parser


def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)  # argparse exits with status 2 on bad usage
    if not args.data_dir.strip():
        parser.error("--data-dir must not be empty")

    try:
        server = create_server(args.data_dir, args.port, args.checker)
    except ValueError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    except OSError as exc:
        print("error: cannot start server: %s" % (exc.strerror or "bind failed"), file=sys.stderr)
        return 1

    try:
        print("Listening on http://127.0.0.1:%d/" % server.server_address[1], flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    finally:
        # serve_forever() has already returned here, so no shutdown() wait is needed.
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
