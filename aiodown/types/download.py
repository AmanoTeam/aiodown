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
import concurrent.futures
import datetime
import httpcore
import httpx
import humanize
import logging
import os
import random

from aiodown.errors import FinishedError, PausedError, ProgressError
from typing import Callable, Union

log = logging.getLogger(__name__)


class Download:
    def __init__(
        self,
        url: str,
        path: str = None,
        retries: int = 3,
        client: "aiodown.Client" = None,
        workers: int = 8,
    ):
        self._client = client
        self._workers = workers

        self._id = random.randint(1, 9999)
        self._url = url
        self._path = os.path.dirname(path) if path else None
        self._name = os.path.basename(path) if path else os.path.basename(url)
        self._start = 0
        self._status = "ready"
        self._retries = retries
        self._attempts = 0
        self._bytes_total = 0
        self._bytes_downloaded = 0

        self._loop = asyncio.get_event_loop()
        self._task = asyncio.ensure_future(self._request())

    async def _request(self):
        """This is where the magic happens, everything is downloaded here.

        Raises:
            FileExistsError: In case the download location already exists.
        """

        if self.get_status() in ["reconnecting", "started"]:
            if not self._path:
                self._path = f"./downloads/{random.randint(1000, 9999)}"

            if not os.path.exists(self._path):
                os.makedirs(self._path)

            path = os.path.join(self._path, self._name)
            if not self.get_status() == "reconnecting":
                if os.path.exists(path):
                    raise FileExistsError(f"[Errno 17] File exists: '{path}'")
                self._status = "downloading"

            try:
                async with httpx.AsyncClient() as client:
                    async with client.stream("GET", self._url) as response:
                        assert response.status_code == 200

                        self._bytes_total = int(response.headers["Content-Length"])

                        async with async_files.FileIO(path, "wb") as file:
                            async for chunk in response.aiter_bytes():
                                if self.get_status() == "stopped":
                                    break
                                if self.get_status() == "paused":
                                    while self.get_status() == "paused":
                                        await asyncio.sleep(0.1)
                                        continue

                                bytes_downloaded = response.num_bytes_downloaded
                                if self.get_status() == "reconnecting":
                                    if bytes_downloaded < self.get_size_downloaded():
                                        continue
                                    else:
                                        self._attempts = 0
                                        self._status = "downloading"

                                if bytes_downloaded > 0:
                                    await file.write(chunk)
                                    self._bytes_downloaded = bytes_downloaded

                            if not self.get_status() == "stopped":
                                self._status = "finished"
                                log.info(f"{self.get_file_name()} finished!")
                                if not self._client is None:
                                    self._client.check_is_running()
                            await file.close()
                    await client.aclose()
            except (
                AssertionError,
                httpx.CloseError,
                httpcore.ConnectError,
                httpx.ConnectError,
                httpx.RemoteProtocolError,
                KeyError,
            ):
                log.info(f"{self.get_file_name()} connection failed!")
                self._status = "reconnecting"
                log.info(f"{self.get_file_name()} retrying!")
                if self.get_attempts() < self.get_retries():
                    await asyncio.sleep(3)
                    self._attempts += 1
                    await self._request()
                else:
                    self._status = "failed"
                    log.info(
                        f"{self.get_file_name()} reached the limit of {self.get_retries()} attempts!"
                    )
            except:
                self._status = "failed"
                log.info(f"{self.get_file_name()} failed!")
                if not self._client is None:
                    self._client.check_is_running()

    async def start(self):
        """Starts the download if it has not already been.

        Raises:
            RuntimeError: If the download has already started.
            :obj:`aiodown.errors.ProgressError`: If the download is in progress.
        """

        if self.get_status() == "started":
            raise RuntimeError("Download is already started")
        if not self.is_finished():
            raise ProgressError()

        self._status = "started"
        self._start = datetime.datetime.now()
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=self._workers)
        future = self._loop.run_in_executor(pool, self._task, self.get_id())
        await asyncio.gather(future, return_exceptions=True)

        log.info(f"{self.get_file_name()} started!")

    async def stop(self):
        """Stop download if started.

        Raises:
            :obj:`aiodown.errors.FinishedError`: In case the download has already been completed.
            RuntimeError: If the download has already stopped.
        """

        if self.is_finished():
            raise FinishedError()
        if self.get_status() == "stopped":
            raise RuntimeError("Download is already stopped")

        self._status = "stopped"
        if not self._task.cancelled():
            self._task.cancel()
        if not self._client is None:
            self._client.check_is_running()

        log.info(f"{self.get_file_name()} stopped!")

    async def pause(self):
        """Pauses the download if it is in progress.

        Raises:
            :obj:`aiodown.errors.FinishedError`: In case the download has already been completed.
            :obj:`aiodown.errors.PausedError`: In case the download is already paused.
        """

        if self.is_finished():
            raise FinishedError()
        if self.get_status() == "paused":
            raise PausedError()

        self._status = "paused"

        log.info(f"{self.get_file_name()} paused!")

    async def resume(self):
        """Resume download if paused.

        Raises:
            :obj:`aiodown.errors.FinishedError`: In case the download has already been completed.
            :obj:`aiodown.errors.ProgressError`: In case download is not paused.
        """

        if self.is_finished():
            raise FinishedError()
        if not self.get_status() == "paused":
            raise ProgressError()

        self._status = "downloading"

        log.info(f"{self.get_file_name()} resumed!")

    def get_size_total(
        self, human: bool = False, binary: bool = False, gnu: bool = False
    ) -> Union[int, str]:
        """Get the total number of bytes.

        Parameters:
            human (``bool``, *optional*):
                If True, it will return the bytes in a format for human understanding,
                if False, it will return only the bytes in numbers.

            binary (``bool``, *optional*):
                If True, it will return the bytes in a format for human understanding in binary mode,
                if False, it will return only in human understanding format.
                ``human`` required.

            gnu (``bool``, *optional*):
                If True, it will return the bytes in a format for human understanding in gnu mode,
                if False, it will return only in human understanding format.
                ``human`` required.

        Raises:
            TypeError: In case of using binary or gnu mode without human mode.
            TypeError: If you try to use binary and gnu mode at the same time.

        Returns:
            ``int``: If human mode is disabled.
            ``str``: If human mode is enabled.
        """

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
        """Get the downloaded number of bytes.

        Parameters:
            human (``bool``, *optional*):
                If True, it will return the bytes in a format for human understanding,
                if False, it will return only the bytes in numbers.

            binary (``bool``, *optional*):
                If True, it will return the bytes in a format for human understanding in binary mode,
                if False, it will return only in human understanding format.
                ``human`` required.

            gnu (``bool``, *optional*):
                If True, it will return the bytes in a format for human understanding in gnu mode,
                if False, it will return only in human understanding format.
                ``human`` required.

        Raises:
            TypeError: In case of using binary or gnu mode without human mode.
            TypeError: If you try to use binary and gnu mode at the same time.

        Returns:
            ``int``: If human mode is disabled.
            ``str``: If human mode is enabled.
        """

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
        """Get the current progress.

        Returns:
            ``float``: The current progress of the download.
        """

        try:
            progress = float(
                f"{self.get_size_downloaded() / self.get_size_total() * 100:.1f}"
            )
        except ZeroDivisionError:
            progress = 0
        return progress

    def get_id(self) -> int:
        """Get the download id.

        Returns:
            ``int``: The download id.
        """

        return self._id

    def get_url(self) -> str:
        """Get the download URL.

        Returns:
            ``str``: The download URL.
        """

        return self._url

    def get_status(self) -> str:
        """Get the download status.

        Returns:
            ``str``: The download status.
        """

        return self._status

    def get_retries(self) -> int:
        """Get the download retries.

        Returns:
            ``int``: The download retries.
        """

        return self._retries

    def get_attempts(self) -> int:
        """Get the download attempts.

        Returns:
            ``int``: The download attempts.
        """

        return self._attempts

    def get_file_path(self) -> str:
        """Get the download location.

        Returns:
            ``str``: The download location.
        """

        return self._path

    def get_file_name(self) -> str:
        """Get the download file name.

        Returns:
            ``str``: The download file name.
        """

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
        """Get the elapsed time bytes.

        Parameters:
            human (``bool``, *optional*):
                If True, it will return the bytes in a format for human understanding,
                if False, it will return only the bytes in numbers.

            precise (``bool``, *optional*):
                If True, it will return you want the precise time.
                if False, it will return only in human understanding format.
                ``human`` required.

        Raises:
            TypeError: In case of using precise mode without human mode.

        Returns:
            ``int``: If human mode is disabled.
            ``str``: If human mode is enabled.
        """

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
        """Get the download speed bytes.

        Parameters:
            human (``bool``, *optional*):
                If True, it will return the bytes in a format for human understanding,
                if False, it will return only the bytes in numbers.

            binary (``bool``, *optional*):
                If True, it will return the bytes in a format for human understanding in binary mode,
                if False, it will return only in human understanding format.
                ``human`` required.

            gnu (``bool``, *optional*):
                If True, it will return the bytes in a format for human understanding in gnu mode,
                if False, it will return only in human understanding format.
                ``human`` required.

        Raises:
            TypeError: In case of using binary or gnu mode without human mode.
            TypeError: If you try to use binary and gnu mode at the same time.

        Returns:
            ``int``: If human mode is disabled.
            ``str``: If human mode is enabled.
        """

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
        """Get the eta time bytes.

        Parameters:
            human (``bool``, *optional*):
                If True, it will return the bytes in a format for human understanding,
                if False, it will return only the bytes in numbers.

            precise (``bool``, *optional*):
                If True, it will return you want the precise time.
                if False, it will return only in human understanding format.
                ``human`` required.

        Raises:
            TypeError: In case of using precise mode without human mode.

        Returns:
            ``int``: If human mode is disabled.
            ``str``: If human mode is enabled.
        """

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
        """Checks whether the download has been completed.

        Returns:
            ``bool``: True if the download has been finished.
        """

        return self.get_status() in ["failed", "finished", "ready", "stopped"]

    def is_success(self) -> bool:
        """Checks whether the download was successful.

        Raises:
            :obj:`aiodown.erros.ProgressError`: If the download has not yet finished.

        Returns:
            ``bool``: True if the download was a success.
        """

        if not self.is_finished():
            raise ProgressError()

        return self.get_status == "finished"

    def __repr__(self) -> str:
        """Get some download details.

        Returns:
            ``str``: Some download details.
        """

        return f"{self.__class__.__name__}(id={self.get_id()}, url={self.self.get_url()}, path={self.get_file_path()}, name={self.self.get_file_name()}, status={self.get_status()})"

    def __str__(self) -> Callable:
        """Get some download details.

        Returns:
            ``str``: Some download details.
        """

        return self.__repr__()
