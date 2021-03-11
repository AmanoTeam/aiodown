from aiodown import (
    __author__ as author,
    __email__ as email,
    __license__ as license,
    __version__ as version,
)
from setuptools import find_packages, setup

with open("README.md", "r") as file:
    readme = file.read()

setup(
    name="aiodown",
    version=version,
    packages=find_packages(),
    install_requires=["async-files>=0.4", "httpx[http2]>=0.14", "humanize>=3.2.0"],
    url="https://github.com/AmanoTeam/aiodown",
    python_requires=">=3.8",
    author=author,
    author_email=email,
    license=license,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: Implementation",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Internet"
    ],
    description="A fully async file downloader",
    download_url="https://github.com/AmanoTeam/aiodown/releases/latest",
    long_description=readme,
    long_description_content_type="text/markdown",
    keywords="python downloader async asyncio httpx",
)
