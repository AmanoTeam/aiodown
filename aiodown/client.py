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


class Client:
    def __init__(self):
        self._httpx = None
        self._downloads = {}
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

        id = len(self._downloads.keys())
        dl = Download(url, path, name, retries, self._httpx)
        dl._id = id
        self._downloads[id] = dl

        return dl

    def rem(self, id: int):
        if id in self._downloads.keys():
            if self._downloads[id].is_finished():
                del self._downloads[id]
            else:
                raise RuntimeError("The download is in progress, cancel it first")
        else:
            raise KeyError(f"There is no download with id '{id}'")

    async def start(self):
        if self.is_running():
            raise RuntimeError("Downloads have already started")

        for _download in self._downloads.values():
            await _download.start()

        self._running = True

    async def stop(self):
        if not self.is_running():
            raise RuntimeError("There is no download in progress")

        for _download in self._downloads.values():
            await _download.stop()

        self._running = False

    async def close(self):
        try:
            await self._httpx.aclose()
        except RuntimeError:
            pass
        self._httpx = None

    def is_running(self) -> bool:
        return self._running

    def get_downloads(self) -> List[Download]:
        return self._downloads.values()