# 第三方组件

本项目自有源码采用 MIT（根目录 LICENSE）。依赖保持各自许可证；本项目不宣称拥有其著作权。

- `sys.lua`、`sysplus.lua`：来自 [openLuat/LuatOS](https://github.com/openLuat/LuatOS) Lua 调度库，保留文件作者注释。上游采用 MIT，附录许可证见 `LICENSES/LuatOS-MIT.txt`。
- LuatOS V2052 Air780EHV `.soc`：从合宙官方 CDN 按固定 SHA-256 获取，属于设备核心固件；不打包进本项目 IPK，不将其声明为本项目 MIT 源码。
- [wendal/luatos-cli](https://github.com/wendal/luatos-cli) v1.11.0：按固定 SHA-256 按需下载的独立烧录工具；遵循其上游许可证（MIT）。工具内置 Lua 编译器遵循 Lua 许可。
- Ubuntu libc6、libgcc-s1、libudev1、libcap2：可选烧录时从官方 Ubuntu 软件池下载的独立运行库，许可包含 LGPL/GPL 及 BSD 等；许可证与对应源码由 Ubuntu 包元数据及官方源码包提供，不在 IPK 中再分发这些库。
- OpenWrt、LuCI、Python、curl、SQLite、OpenSSL、zstd：由用户固件软件源安装，分别遵循上游许可。

发行 IPK 只包含本项目 Python/Lua/网页/启动脚本和许可证。完整项目源码在同一仓库公开，包含构建脚本、测试及配套模块脚本。源码包不含 SIM 信息、短信、邮箱密码、路由器配置、签名私钥或下载的核心固件/运行库。
