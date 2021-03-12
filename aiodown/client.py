# MIT License
#
# Copyright (c) 2021 Amano Team
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import httpx
import logging

from aiodown.types import Download
from typing import List

log = logging.getLogger("aiodown")


class Client:
    def __init__(self):
        self._httpx = None
        self._downloads = []
        self._running = False

    async def __aenter__(self):
        self._httpx = httpx.AsyncClient()
        return self

    async def __aexit__(self, *args):
        return self

    def add(
        self, url: str, path: str = None, name: str = None, retries: int = 3
    ) -> Download:
        if self.is_running():
            raise RuntimeError(
                "Downloads have already started, cancel them or wait for them to finish"
            )

        dl = Download(url, path, name, retries, self._httpx)
        self._downloads.append(dl)

        log.info("A new file was added")

        return dl

    async def start(self):
        if self.is_running():
            raise RuntimeError("Downloads have already started")

        for _download in self._downloads:
            await _download.start()

        self._running = True

        log.info(f"{len(self._downloads)} downloads have started")

    async def stop(self):
        if not self.is_running():
            raise RuntimeError("There is no download in progress")

        for index, _download in enumerate(self._downloads):
            await _download.stop()
            del self._downloads[index]

        self._running = False

        log.info(f"{len(self._downloads)} downloads have stopped")

    async def close(self):
        try:
            await self._httpx.aclose()
        except RuntimeError:
            pass
        self._httpx = None

    def is_running(self) -> bool:
        return self._running

    def get_downloads(self) -> List[Download]:
        return self._downloads
