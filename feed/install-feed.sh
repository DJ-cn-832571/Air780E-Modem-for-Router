#!/bin/sh
set -eu
base='https://raw.githubusercontent.com/832571/Air780E-Modem-for-Router/codex/release-v1.3/feed'
fingerprint='af5c2a6ce4ab8132'
[ "$(id -u)" = 0 ] || { echo '请使用路由器 root 执行'; exit 1; }
case "${1:-}" in ''|--feed-only) ;; *) echo '用法：install-feed.sh [--feed-only]'; exit 1;; esac
for tool in opkg usign curl gzip; do command -v "$tool" >/dev/null || { echo "缺少依赖：$tool"; exit 1; }; done
work=$(mktemp -d /tmp/air780e-feed.XXXXXX)
trap 'rm -rf "$work"' EXIT HUP INT TERM
fetch() { curl -4 --retry 3 --retry-delay 1 --fail --location --proto '=https' --proto-redir '=https' --connect-timeout 15 --max-time 120 "$base/$1" -o "$work/$1"; }
fetch feed.pub
[ "$(usign -F -p "$work/feed.pub")" = "$fingerprint" ] || { echo '软件源公钥指纹不匹配'; exit 1; }
fetch Packages.gz
fetch Packages.sig
gzip -dc "$work/Packages.gz" > "$work/Packages"
usign -V -m "$work/Packages" -p "$work/feed.pub" -x "$work/Packages.sig"
mkdir -p /etc/opkg/keys
cp "$work/feed.pub" "/etc/opkg/keys/$fingerprint"
chmod 644 "/etc/opkg/keys/$fingerprint"
feed=/etc/opkg/customfeeds.conf
[ ! -f "$feed" ] || cp "$feed" "$feed.air780e-backup"
if [ -f "$feed" ]; then
 sed '/^[[:space:]]*src\/gz[[:space:]]\+air780e_router[[:space:]]/d' "$feed" > "$work/customfeeds.conf"
else : > "$work/customfeeds.conf"; fi
printf '\nsrc/gz air780e_router %s\n' "$base" >> "$work/customfeeds.conf"
cp "$work/customfeeds.conf" "$feed"
lists=$(awk '$1=="lists_dir" {print $3; exit}' /etc/opkg.conf)
lists=${lists:-/var/opkg-lists}
check_index() {
 [ -f "$lists/air780e_router" ] || return 1
 if gzip -t "$lists/air780e_router" 2>/dev/null; then
  gzip -dc "$lists/air780e_router" > "$work/index-installed"
 else cp "$lists/air780e_router" "$work/index-installed"; fi
 cmp -s "$work/Packages" "$work/index-installed"
}
ready=0
for attempt in 1 2 3; do
 if ! opkg update; then echo '部分软件源更新失败，正在检查本项目源'; fi
 if check_index; then ready=1; break; fi
 echo "本项目索引未就绪，重试 $attempt / 3"
done
[ "$ready" = 1 ] || { echo '本项目签名索引未成功更新，停止安装'; exit 1; }
if [ "${1:-}" != --feed-only ]; then opkg install luci-app-air780e; fi
echo '软件源已配置；LuCI 软件包页可搜索 luci-app-air780e。'
