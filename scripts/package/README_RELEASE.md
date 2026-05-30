# CandleTRPG-LAN 运行包

## 启动

双击 `start.bat`。

启动后会打开浏览器：

```text
http://127.0.0.1:5173
```

后端默认运行在：

```text
http://127.0.0.1:8001
```

## 局域网联机

房主运行 `start.bat` 后，其他玩家在前端主菜单的“服务器地址”里填写房主电脑的局域网地址，例如：

```text
http://192.168.1.23:8001
```

房主电脑需要允许 Windows 防火墙访问 `8001` 端口。

## AI 配置

如果后端需要 OpenAI 或兼容服务，请编辑运行包里的 `.env` 文件。

示例：

```env
OPENAI_API_KEY=你的key
OPENAI_BASE_URL=
OPENAI_MODEL=gpt-4o-mini
```

## 关闭

关闭启动后出现的 `CandleTRPG Backend` 和 `CandleTRPG Frontend` 两个命令行窗口即可。
