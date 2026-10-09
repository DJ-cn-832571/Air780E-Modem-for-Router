# Changelog

[简体中文](CHANGELOG.md) | **English**

## V1.3 / 1.3.3

- Add Stock code: 832571 immediately after DJ Networking in the footer and About information.
- Add Simplified Chinese, English and Traditional Chinese UI; default to Simplified Chinese and remember explicit browser choices.
- Translate interface text, statuses, confirmations and service messages while preserving SMS bodies, form input and protocol confirmation tokens.
- Provide English README, network policy, troubleshooting, release maintenance, third-party notices and changelog; add English descriptions to existing GitHub Releases.

## V1.3 / 1.3.2

- Add per-record deletion to Sent, select-all for the displayed page and bulk deletion below the list.
- Move deleted sent records into Trash, supporting restoration and preserving send outcomes. Migrate existing databases without losing history.
- Clear selections on tab changes; support indeterminate selection and disabled controls for empty lists.
- Pass 31 automated tests and real LuCI single/bulk deletion and restoration checks.

## V1.3 / 1.3.1

- Use a static GitHub feed compatible with GL's native downloader, retaining usign signatures and TLS validation.
- Update the current GitHub account name to DJ-cn-832571.
- Continue installation after unrelated vendor-feed failures only if this project's verified index was successfully stored.

## V1.3 / 1.3.0

- First public router release with full project source under MIT.
- Provide IPK, signed opkg feed, installer and documentation.
- Port module status, SMS management, forwarding and firmware tools from Mac 0.9.3.
- Fix USB re-enumeration Errno 19, system-DNS curl 6 and unsupported browser prompt dialogs.
- Compile firmware scripts using an isolated GNU loader and check them before entering download mode.
- Prefer Air780E with WAN backup, wait for DHCP at startup and provide LAN NAT.
- Verify actual MT3000 flashing and three start/stop/fallback cycles; pass 29 regression tests.
