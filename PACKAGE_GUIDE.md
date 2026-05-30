# CandleTRPG-LAN 方案二打包说明

方案二生成的是一个本地运行包：用户双击 `start.bat` 后，会在本机启动 FastAPI 后端和前端静态服务。

## 生成运行包

在项目根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_offline_package.ps1
```

生成目录：

```text
release\CandleTRPG-LAN
```

把这个文件夹压缩后发给别人即可。

## 用户如何启动

用户解压后双击：

```text
start.bat
```

默认地址：

```text
前端：http://127.0.0.1:5173
后端：http://127.0.0.1:8001
```

## 局域网模式

房主启动运行包后，其他玩家在前端主菜单的“服务器地址”里填写房主电脑的局域网 IP：

```text
http://192.168.1.23:8001
```

房主后端已经按 `0.0.0.0:8001` 启动，可以被同一局域网访问。若连接失败，通常是 Windows 防火墙没有放行 `8001` 端口。

## 离线依赖

默认打包脚本会下载 Python wheel 到运行包的 `wheelhouse` 目录。用户第一次运行 `start.bat` 时，会优先从 `wheelhouse` 安装依赖，不需要联网。

如果你只想生成较小的包，可以跳过 wheel：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_offline_package.ps1 -SkipWheelhouse
```

这种包第一次运行时需要联网安装 Python 依赖。

## 前置要求

打包机器需要：

- Node.js
- Python 3.11+
- npm

用户机器需要：

- Python 3.11+

如果未来要做到用户完全不需要安装 Python，需要再升级到 PyInstaller 或 Electron/Tauri 方案。
