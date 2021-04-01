from setuptools import find_packages, setup

with open("README.md", "r") as file:
    readme = file.read()
    file.close()

with open("CHANGELOG.md", "r") as file:
    readme += "\n\n"
    readme += file.read()
    file.close()

setup(
    name="aiodown",
    version="1.0.5",
    packages=find_packages(),
    install_requires=[
        "async-files >= 0.4",
        "httpx[http2] >= 0.14",
        "humanize >= 3.2.0",
    ],
    url="https://github.com/AmanoTeam/aiodown",
    python_requires=">=3.8",
    author="AmanoTeam",
    author_email="contact@amanoteam.com",
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: Implementation",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Internet",
    ],
    description="A fully async file downloader with httpx",
    download_url="https://github.com/AmanoTeam/aiodown/releases/latest",
    long_description=readme,
    long_description_content_type="text/markdown",
    keywords="python, downloader, async, asyncio, httpx, file",
    project_urls={
        "Bug report": "https://github.com/AmanoTeam/aiodown/issues",
        "Donate": "https://liberapay.com/AmanoTeam",
        "Source": "https://github.com/AmanoTeam/aiodown",
    },
)
