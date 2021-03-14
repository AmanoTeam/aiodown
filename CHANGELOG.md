# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## 1.0.4 (March 14th, 2021)

### Added

* Assert that the status code is 200.

### Changed

* Improve code based on Codacy.
* The downloads are runned in a executor instead of threads.

## 1.0.3 (March 13th, 2021)

### Added

* `aiodown.errors` package.

## 1.0.2 (March 13th, 2021)

### Added

* `client.rem()` method.
* `download.get_attempts()`, `download.get_id()`, `download.get_retries()` and `download.get_start_time()` methods.

## 1.0.1 (March 12th, 2021)

### Added

* Support for download retries.
* `await download.resume()` method.

### Changed

* `client.add()` instead of `client.download()` method.

## 1.0.0 (March 12th, 2021)

* First release.