"""`teamdev-test-runner` のエントリポイント。

    uv run --project tools/teamdev-test-runner-mcp teamdev-test-runner
"""

from .server import run


def main() -> None:
    run()


if __name__ == "__main__":
    main()
