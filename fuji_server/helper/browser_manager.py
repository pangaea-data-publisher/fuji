# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

import logging

from playwright.async_api import async_playwright


class BrowserManager:
    _playwright = None
    _browser = None
    logger = logging.getLogger(__name__)

    @classmethod
    async def init_browser(cls):
        """Initialize Playwright async instance and a single shared browser."""
        if cls._browser is not None:
            return cls._browser

        cls.logger.info("Starting Playwright (async)...")

        cls._playwright = await async_playwright().start()
        cls._browser = await cls._playwright.chromium.launch(headless=False)

        cls.logger.info("Playwright browser launched")
        return cls._browser

    @classmethod
    async def stop_browser(cls):
        """Shutdown browser + Playwright."""
        cls.logger.info("Stopping Playwright...")

        if cls._browser:
            await cls._browser.close()
            cls._browser = None

        if cls._playwright:
            await cls._playwright.stop()
            cls._playwright = None

        cls.logger.info("Playwright stopped")
