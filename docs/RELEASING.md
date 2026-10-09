# 发布维护

1. 运行测试，同步服务、页面、构建脚本的版本号。
2. `python3 scripts/build.py` 生成 IPK，`python3 scripts/build-feed.py` 生成 Packages / Packages.gz。
3. 使用私下保存的 usign 密钥：`usign -S -m dist/Packages -s /private/path/feed.sec -x dist/Packages.sig`。
4. 用 `feed.pub` 验证索引签名。生成源码归档及 SHA256SUMS，核对 IPK 不含数据库、密码、配置和私钥。
5. 发布 GitHub Release，所有 feed 文件与 IPK 必须上传到同一 Release：Packages、Packages.gz、Packages.sig、feed.pub、install-feed.sh、IPK、SHA256SUMS、源码归档。
6. 从路由器执行安装脚本并更新列表，核验 LuCI 软件包页能搜索到正确版本，再安装验证。

签名链：固定公钥指纹 → Packages.sig → Packages 内的 IPK SHA256sum。密钥只在维护者私下保存；不提交到 GitHub。丢失私钥后不能继续沿用同一公钥，须明确发布密钥迁移说明。

首次配置第三方源意味着信任该维护者的后续版本，应先阅读安装脚本、公钥指纹及源码。GitHub latest/download 自动跟随最新稳定发布。发布包不是官方 OpenWrt/GL.iNet 软件源收录；官方收录须另行申请。
