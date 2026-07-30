# TrollRestore macOS 版

巨魔安装器 macOS 桌面版，通过 pymobiledevice3 连接 iPhone/iPad 安装 TrollStore。

## 环境要求
- macOS 10.15+
- Python 3.9+
- iPhone/iPad USB 连接

## 快速开始
```bash
pip install PyQt5 qasync pymobiledevice3 packaging requests
```

将 Windows 版同目录下的 `sparserestore/` 文件夹和 `PersistenceHelper_Embedded` 文件复制到本目录，然后：

```bash
python3 trollrestore_mac.py
```

## 打包为 App
```bash
# PyInstaller（简单）
pip install pyinstaller
pyinstaller --onefile --windowed \
    --name "TrollRestore" \
    --add-data "sparserestore:sparserestore" \
    --add-data "PersistenceHelper_Embedded:." \
    trollrestore_mac.py
```

## 与 Windows 版的区别
- 无需驱动检测（macOS 内置 usbmuxd）
- 字体使用系统默认（苹方/PingFang SC）
- 数据存在 `~/Library/Application Support/TrollRestore/`
- 无环境检测弹窗
