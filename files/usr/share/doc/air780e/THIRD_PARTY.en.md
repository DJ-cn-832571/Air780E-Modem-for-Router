# Third-party components

[简体中文](THIRD_PARTY.md) | **English**

Project-owned source uses MIT; see the root LICENSE. Dependencies retain their own licenses. This project does not claim their copyrights.

- `sys.lua`, `sysplus.lua`: Lua scheduling libraries from [openLuat/LuatOS](https://github.com/openLuat/LuatOS), retaining author comments. Upstream uses MIT; see `LICENSES/LuatOS-MIT.txt`.
- LuatOS V2052 Air780EHV `.soc`: device core firmware downloaded from the official AirM2M CDN with pinned SHA-256. Not included in the IPK and not claimed as project-owned MIT source.
- [wendal/luatos-cli](https://github.com/wendal/luatos-cli) v1.11.0: independent on-demand flashing tool with pinned SHA-256, under upstream MIT. Its embedded Lua compiler follows the Lua license.
- Ubuntu libc6, libgcc-s1, libudev1 and libcap2: optional flashing runtime libraries downloaded from official Ubuntu package pools. Licenses include LGPL/GPL and BSD variants; license information and corresponding sources are provided by Ubuntu package metadata and source packages. These libraries are not redistributed in the IPK.
- OpenWrt, LuCI, Python, curl, SQLite, OpenSSL and zstd: installed from the user's firmware feed under their respective upstream licenses.

The IPK contains project Python/Lua/web/startup scripts and license notices. Complete project source is public in the same repository, including build scripts, tests and companion module scripts. Source archives exclude SIM information, SMS, mailbox passwords, router configuration, private signing keys and downloaded core firmware/runtime libraries.

Traditional Chinese catalog text was generated during development using OpenCC and reviewed for UI terminology. OpenCC is not a router runtime dependency; no OpenCC code is bundled in the IPK.
