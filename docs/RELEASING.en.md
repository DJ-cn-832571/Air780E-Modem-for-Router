# Release maintenance

[简体中文](RELEASING.md) | **English**

1. Run tests and synchronize version numbers in the service, page and build scripts.
2. Run `python3 scripts/build.py` for the IPK and `python3 scripts/build-feed.py` for Packages / Packages.gz.
3. Sign with the privately stored usign key: `usign -S -m dist/Packages -s /private/path/feed.sec -x dist/Packages.sig`.
4. Verify the index with `feed.pub`. Generate the source archive and SHA256SUMS. Ensure the IPK contains no databases, passwords, user configuration or private keys.
5. Publish a GitHub Release containing Packages, Packages.gz, Packages.sig, feed.pub, install-feed.sh, IPK, SHA256SUMS and the source archive.
6. Run the installer from a router, update package lists, verify LuCI finds the correct version and test installation.

Trust chain: pinned public-key fingerprint → Packages.sig → the IPK SHA256sum in Packages. Keep private keys outside GitHub. Losing the private key requires an explicit key migration; the old public key cannot sign new indexes.

Adding a third-party feed trusts the maintainer's future packages. Review the installer, fingerprint and source first. `feed/` provides stable static downloads for GL downloaders that cannot handle Release redirects. Releases also provide source and signed-index backups. Official OpenWrt/GL.iNet inclusion requires a separate application.

After signing, synchronize the IPK, Packages, Packages.gz, Packages.sig, public key and installer into `feed/`, then commit and publish. Do not overwrite existing release tags; use patch versions for feed fixes.

Keep Chinese and English documentation, release descriptions and language catalogs aligned. UI changes must preserve SMS bodies, form drafts and exact RPC confirmation tokens. Test all three languages on the router before release.
