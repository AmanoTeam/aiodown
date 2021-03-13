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

from aiodown.errors import FinishedError, PausedError, ProgressError
from typing import Callable, Union

log = logging.getLogger("aiodown.download")


class Download:
    def __init__(
        self,
        url: str,
        path: str = None,
        retries: int = 3,
        client: "aiodown.Client" = None,
    ):
        self._client = client

        self._id = random.randint(1, 9999)
        self._url = url
        self._path = path
        self._name = (
            os.path.basename(path)
            if (path and ("." in path.split("/")[-1]))
            else os.path.basename(url)
        )
        self._start = 0
        self._status = "ready"
        self._retries = retries
        self._attempts = 0
        self._bytes_total = 0
        self._bytes_downloaded = 0

        self._thread = threading.Thread(target=self._start_download)
        self._thread.daemon = True

    def _start_download(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._download())

    async def _download(self):
        if self.get_status() in ["reconnecting", "started"]:
            if not self._path:
                self._path = f"./downloads/{random.randint(1000, 9999)}"

            if not os.path.exists(self._path):
                os.makedirs(self._path)

            path = os.path.join(self._path, self._name)
            if os.path.exists(path):
                raise FileExistsError(f"[Errno 17] File exists: '{path}'")

            try:
                async with httpx.AsyncClient() as client:
                    async with client.stream("GET", self._url) as response:
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
                                log.info(f"{self.get_file_name()} finished!")
                                if not self._client is None:
                                    self._client.check_is_running()
                            await file.close()
                    await client.aclose()
            except (httpx.RemoteProtocolError, KeyError):
                log.info(f"{self.get_file_name()} connection failed!")
                self._status = "reconnecting"
                log.info(f"{self.get_file_name()} retrying!")
                if self.get_attempts() <= self.get_retries():
                    self._attempts += 1
                    await self._download()
                else:
                    self._status = "failed"
                    log.info(
                        f"{self.get_file_name()} reached the limit of {self.get_retries()} attempts!"
                    )
            except Exception as excep:
                self._status = "failed"
                log.info(f"{self.get_file_name()} failed!")
                if not self._client is None:
                    self._client.check_is_running()
                raise excep.__class__(excep)

    async def start(self):
        if self.get_status() == "started":
            raise RuntimeError("Download is already started")
        if not self.is_finished():
            raise ProgressError()

        self._status = "started"

        log.info(f"{self.get_file_name()} started!")

        self._start = datetime.datetime.now()
        self._thread.start()

    async def stop(self):
        if self.is_finished():
            raise FinishedError()
        if self.get_status() == "stopped":
            raise RuntimeError("Download is already stopped")

        self._status = "stopped"
        if not self._client is None:
            self._client.check_is_running()

        log.info(f"{self.get_file_name()} stopped!")

    async def pause(self):
        if self.is_finished():
            raise FinishedError()
        if self.get_status() == "paused":
            raise PausedError()

        self._status = "paused"

        log.info(f"{self.get_file_name()} paused!")

    async def resume(self):
        if self.is_finished():
            raise FinishedError()
        if not self.get_status() == "paused":
            raise ProgressError()

        self._status = "downloading"

        log.info(f"{self.get_file_name()} resumed!")

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
            progress = float(
                f"{self.get_size_downloaded() / self.get_size_total() * 100:.1f}"
            )
        except ZeroDivisionError:
            progress = 0
        return progress

    def get_id(self) -> int:
        return self._id

    def get_url(self) -> str:
        return self._url

    def get_status(self) -> str:
        return self._status

    def get_retries(self) -> int:
        return self._retries

    def get_attempts(self) -> int:
        return self._attempts

    def get_file_path(self) -> str:
        return self._path

    def get_file_name(self) -> str:
        return self._name

    def get_start_time(
        self, human: bool = False, precise: bool = False
    ) -> Union[int, str]:
        time = self._start

        if precise and not human:
            raise TypeError("To get accurate time, activate human mode")

        if human:
            if precise:
                return humanize.precisedelta(time)
            else:
                return humanize.naturaltime(time)
        return time

    def get_elapsed_time(
        self, human: bool = False, precise: bool = False
    ) -> Union[int, str]:
        time = datetime.datetime.now() - self.get_start_time()

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
        speed = self.get_size_downloaded() / (
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
                seconds=(self.get_size_total() - self.get_size_downloaded())
                / self.get_speed()
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
        return f"{self.__class__.__name__}(id={self.get_id()}, url={self.self.get_url()}, path={self.get_file_path()}, name={self.self.get_file_name()}, status={self.get_status()})"

    def __str__(self) -> Callable:
        return self.__repr__()
