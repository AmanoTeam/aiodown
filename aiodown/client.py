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

from aiodown.types import Download
from typing import List, Union


class Client:
    """aiodown Client, where you can remove and/or add files from/in the download list.

    Parameters:
        workers (``int``, *optional*):
            Number of workers for each download
            Default to 8.
    """

    def __init__(self, workers: int = 8):
        self._workers = workers
        self._running = False
        self._downloads = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    def add(
        self, url: str, path: str = None, retries: int = 3, workers: int = None
    ) -> Download:
        """Adds a file to the download list.

        Parameters:
            url (``str``):
                Direct file link.

            path (``str``, *optional*):
                File download location.

            retries (``int``, *optional*):
                Number of download retries in case of failure.

            workers (``int``, *optional*):
                Number of workers for each download.
                Default to 8.

        Returns:
            :obj:`aiodown.types.Download`: The download object.
        """

        if self.is_running():
            raise RuntimeError(
                "There are some downloads in progress, cancel them first or wait for them to finish"
            )

        dl_id = len(self._downloads.keys())
        dl = Download(url, path, retries, self, workers if workers else self._workers)
        dl._id = dl_id
        self._downloads[dl_id] = dl

        return dl

    def rem(self, dl_id: Union[bool, int]):
        """Removes one or all files from the download list.

        Parameters:
            dl_id (``int``, ``True``):
                Removes the download from the list with the specified id,
                if True removes all downloads from the list.

        Raises:
            KeyError: In case the dl_id is invalid.
            RuntimeError: In case of have a download in progress.
            TypeError: In case the dl_id is False.
        """

        if isinstance(dl_id, bool):
            if dl_id:
                if self.is_running():
                    raise RuntimeError(
                        "There are some downloads in progress, cancel them first or wait for them to finish"
                    )
                else:
                    self._downloads = {}
            else:
                raise TypeError(
                    "You can only use 'client.rem(True)' or 'client.rem(id)' and not 'client.rem(False)'"
                )
        else:
            if dl_id in self._downloads.keys():
                if self._downloads[dl_id].is_finished():
                    del self._downloads[dl_id]
                else:
                    raise RuntimeError("The download is in progress, cancel it first")
            else:
                raise KeyError(f"There is no download with id '{dl_id}'")

    async def start(self):
        """Starts all downloads in the list.

        Raises:
            RuntimeError: In case of have a download in progress."""

        if self.is_running():
            raise RuntimeError("Downloads have already started")

        for _download in self._downloads.values():
            await _download.start()

        self._running = True

    async def stop(self):
        """Stop all downloads in the list.

        Raises:
            RuntimeError: In case of not have a download in progress."""

        if not self.is_running():
            raise RuntimeError("There is no download in progress")

        for _download in self._downloads.values():
            await _download.stop()

        self._running = False

    def check_is_running(self):
        """Checks if a download is still in progress."""

        for _download in self._downloads.values():
            if _download.is_finished():
                continue
            else:
                return

        self._running = False

    def is_running(self) -> bool:
        """Checks whether the client is running.

        Returns:
            ``bool``: Whether it's running or not.
        """

        return self._running

    def get_downloads(self) -> List[Download]:
        """Get the list of downloads.

        Returns:
            List of :obj:`aiodown.types.Download`: List of download objects.
        """

        return self._downloads.values()
