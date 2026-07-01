import argparse

import uvicorn


def parse_args():
    parser = argparse.ArgumentParser(description="Run the sim_atlas server.")
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind the server to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind the server to (default: 8000)",
    )
    parser.add_argument(
        "--reload", action="store_true", help="Enable auto-reload for development"
    )
    parser.add_argument(
        "--workers", type=int, default=1, help="Number of worker processes (default: 1)"
    )
    parser.add_argument(
        "--root-path",
        type=str,
        default="",
        help="Root path for the application (default: '')",
    )
    parser.add_argument(
        "--forwarded-allow-ips",
        type=str,
        default="127.0.0.1",
        help="Comma-separated list of IPs to allow for forwarding (default: '127.0.0.1')",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    uvicorn.run(
        "sim_atlas.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers,
        root_path=args.root_path,
        forwarded_allow_ips=args.forwarded_allow_ips,
    )
