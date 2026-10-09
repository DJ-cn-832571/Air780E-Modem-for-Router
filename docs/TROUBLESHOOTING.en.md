# Troubleshooting

[简体中文](TROUBLESHOOTING.md) | **English**

- **Package missing:** configure the third-party feed, update LuCI lists and search for `luci-app-air780e`. Check router DNS, time, HTTPS and GitHub reachability if updating fails.
- **Dependency failure:** use the router firmware's own official feed; check storage and kernel-driver versions. Do not use `--force-depends` or mix kernel drivers. apk firmware requires a separate package.
- **USB errors:** check power and data cable, wait for re-enumeration after reconnecting and connect only one supported module. Check `/dev/ttyACM*`, kmod-usb-acm and ECM drivers.
- **DHCP timeout:** verify companion scripts, ECM state and absence of a 192.168.10.0/24 subnet conflict.
- **DHCP works but 4G verification fails:** check SIM data service, signal and module forwarding. Diagnostics distinguish module DNS from HTTPS. Verification binds the module source address; WAN/VPN success is not substituted for 4G success.
- **Old page after update:** refresh the browser and, if needed, restart uhttpd. Diagnose the cause instead of rebooting the whole router.
- **Firmware download fails:** use Prepare firmware tools, check GitHub, Ubuntu package pools, AirM2M CDN and temporary storage. Resource validation and script compilation must pass before flashing.
- **Email authentication fails:** check app password and SSL/STARTTLS, save settings and retry testing. Unknown delivery results are not retried automatically to avoid duplicate disclosure of verification codes.
- **SMS outcome unknown:** inspect Sent before sending again. SMS center acceptance does not guarantee delivery.
- **Language:** choose 简体中文, English or 繁體中文 at the top. First use defaults to Simplified Chinese. A choice is saved in this browser; changing language does not translate SMS bodies or change drafts.
- **Sent deletion:** use the per-record Delete button or select records and use Delete selected below the list. Select-all covers only displayed records. Restore from Trash if necessary. Empty trash permanently deletes received and sent records in Trash.

## Uninstall and data

`opkg remove luci-app-air780e` stops the service and retains `/etc/air780e/`. The directory contains SMS and credentials and is readable only by root. Remove this project's feed line from `/etc/opkg/customfeeds.conf` and its key from `/etc/opkg/keys/af5c2a6ce4ab8132` if needed; retain unrelated feeds and keys.

Back up before permanent cleanup. Permanent deletion is not recoverable through the application, so there is no default automatic cleanup command. Removing the feed or plugin does not restore earlier WAN, VPN or IPv6 policy; see [Network policy](NETWORK.en.md).
