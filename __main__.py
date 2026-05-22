from __future__ import annotations

import asyncio

from .app import ZelzalApplication
from .config import Settings


def main() -> None:
    settings = Settings.from_env()
    asyncio.run(ZelzalApplication(settings).run())


if __name__ == "__main__":
    main()

