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

import asyncio
import async_files
import datetime
import httpx
import humanize
import logging
import os
import random
import threading
import sys

from typing import Callable, Union

log = logging.getLogger("aiodown")


class Download:
    def __init__(
        self, httpx: httpx.AsyncClient, url: str, path: str = None, name: str = None
    ):
        if httpx is None:
            self._httpx = httpx.AsyncClient()
        else:
            self._httpx = httpx

        self._url = url
        self._path = path
        self._name = (
            name if name else os.path.basename(path) if path else os.path.basename(url)
        )
        self._start = 0
        self._status = "ready"
        self._bytes_total = 0
        self._bytes_downloaded = 0

        self._thread = threading.Thread(target=self._start_download)
        self._thread.daemon = True

    def _start_download(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._download())

    async def _download(self):
        if self.get_status() == "started":
            path = self._path
            if not path:
                path = f"./downloads/{random.randint(1000, 9999)}"

            if not os.path.exists(path):
                os.makedirs(path)

            self._path = path

            path = os.path.join(path, self._name)
            if os.path.exists(path):
                raise FileExistsError(f"[Errno 17] File exists: '{path}'")

            try:
                async with self._httpx.stream("GET", self._url) as response:
                    self._status = "downloading"
                    self._bytes_total = int(response.headers["Content-Length"])
                    self._bytes_downloaded = response.num_bytes_downloaded

                    async with async_files.FileIO(path, "wb") as file:
                        async for chunk in response.aiter_bytes():
                            if self.get_status() == "stopped":
                                break
                            if self.get_status() == "paused":
                                while self.get_status() == "paused":
                                    await asyncio.sleep(0.1)
                                    continue

                            await file.write(chunk)

                            self._bytes_downloaded = response.num_bytes_downloaded

                        if not self.get_status() == "stopped":
                            self._status = "finished"
                            log.info(f"{self._name} finished!")
                        await file.close()
            except Exception as excep:
                self._status = "failed"
                log.info(f"{self._name} failed!")
                raise excep.__class__(excep)

    async def start(self):
        if self.get_status() == "started":
            raise RuntimeError("Download is already started")
        if not self.is_finished():
            raise RuntimeError("Download is already in progress")

        self._status = "started"

        log.info(f"{self._name} started!")

        self._start = datetime.datetime.now()
        self._thread.start()

    async def stop(self):
        if self.get_status() == "paused":
            raise RuntimeError("Download is already stopped")
        if self.is_finished():
            raise RuntimeError("Download is already finished")

        self._status = "stopped"

        log.info(f"{self._name} stopped!")

        sys.exit(0)

    async def pause(self):
        if self.get_status() == "paused":
            raise RuntimeError("Download is already paused")
        if self.is_finished():
            raise RuntimeError("Download is already finished")

        self._status = "paused"

        log.info(f"{self._name} paused!")

    def get_size_total(
        self, human: bool = False, binary: bool = False, gnu: bool = False
    ) -> Union[int, str]:
        size = self._bytes_total

        if (binary or gnu) and not human:
            raise TypeError(
                "For 'binary' or 'gnu' type you need to activate human size"
            )

        if binary and gnu:
            raise TypeError(
                "You can only choose one type, 'binary' or 'gnu' and not both at the same time"
            )

        if human:
            return humanize.naturalsize(size, binary=binary, gnu=gnu)
        return size

    def get_size_downloaded(
        self, human: bool = False, binary: bool = False, gnu: bool = False
    ) -> Union[int, str]:
        size = self._bytes_downloaded

        if (binary or gnu) and not human:
            raise TypeError(
                "For 'binary' or 'gnu' type you need to activate human size"
            )

        if binary and gnu:
            raise TypeError(
                "You can only choose one type, 'binary' or 'gnu' and not both at the same time"
            )

        if human:
            return humanize.naturalsize(size, binary=binary, gnu=gnu)
        return size

    def get_progress(self) -> float:
        try:
            progress = float(f"{self._bytes_downloaded / self._bytes_total * 100:.1f}")
        except ZeroDivisionError:
            progress = 0
        return progress

    def get_url(self) -> str:
        return self._url

    def get_status(self) -> str:
        return self._status

    def get_file_path(self) -> str:
        return self._path

    def get_file_name(self) -> str:
        return self._name

    def get_elapsed_time(
        self, human: bool = False, precise: bool = False
    ) -> Union[int, str]:
        time = datetime.datetime.now() - self._start

        if precise and not human:
            raise TypeError("To get accurate time, activate human mode")

        if human:
            if precise:
                return humanize.precisedelta(time)
            else:
                return humanize.naturaltime(time)
        return time

    def get_speed(
        self, human: bool = False, binary: bool = False, gnu: bool = False
    ) -> Union[int, str]:
        speed = self._bytes_downloaded / (
            (datetime.datetime.now() - self._start).seconds + 1
        )

        if (binary or gnu) and not human:
            raise TypeError(
                "For 'binary' or 'gnu' type you need to activate human size"
            )

        if binary and gnu:
            raise TypeError(
                "You can only choose one type, 'binary' or 'gnu' and not both at the same time"
            )

        if human:
            return humanize.naturalsize(speed, binary=binary, gnu=gnu)
        return speed

    def get_eta(self, human: bool = False, precise: bool = False) -> Union[int, str]:
        try:
            time = datetime.timedelta(
                seconds=(self._bytes_total - self._bytes_downloaded) / self.get_speed()
            )
        except ZeroDivisionError:
            time = datetime.timedelta(seconds=0)

        if precise and not human:
            raise TypeError("To get accurate time, activate human mode")

        if human:
            if precise:
                return humanize.precisedelta(time)
            else:
                return humanize.naturaltime(time)
        return time

    def is_finished(self) -> bool:
        return self.get_status() in ["failed", "finished", "ready", "stopped"]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(url={self.self.get_url()}, path={self.get_file_path()}, name={self.self.get_file_name()}, status={self.get_status()})"

    def __str__(self) -> Callable:
        return self.__repr__()
