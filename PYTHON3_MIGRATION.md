# Python 2 到 Python 3 遷移總結

本文件記錄了 Wacom Utility 專案從 Python 2 升級到 Python 3 的所有更改。

## 概述
此專案已完全升級以支持 Python 3（3.7+）。主要改變包括：

### 1. **Shebang 更新**
- `#!/usr/bin/env python2` → `#!/usr/bin/env python3`
- 所有主要 Python 文件都已更新

### 2. **GTK 版本升級（GTK 2 → GTK 3）**

#### 移除的舊庫：
- `import gtk` 
- `import gtk.glade`
- `import pygtk`
- `import gobject`
- `gtk.gdk` 

#### 新的 GTK 3 導入：
```python
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject
```

#### API 變更：
| 舊 (GTK 2) | 新 (GTK 3) |
|-----------|-----------|
| `gtk.main()` | `Gtk.main()` |
| `gtk.main_quit()` | `Gtk.main_quit()` |
| `gtk.glade.XML()` | `Gtk.Builder()` + `builder.add_from_file()` |
| `widget.get_widget()` | `builder.get_object()` |
| `gtk.Label()` | `Gtk.Label()` |
| `gtk.HBox()` | `Gtk.HBox()` |
| `gtk.DrawingArea` | `Gtk.DrawingArea` |
| `gtk.gdk.*` | `Gdk.*` |
| `gobject.timeout_add()` | `GObject.timeout_add()` |

### 3. **進程執行升級**
替換了所有的 `os.popen()` 調用為 `subprocess.run()` 或 `subprocess.Popen()`：

#### 舊方法：
```python
devlist = os.popen("xsetwacom --list devices").readlines()
data = os.popen("xsetwacom get '" + device + "' " + function).read()
```

#### 新方法：
```python
result = subprocess.run(["xsetwacom", "--list", "devices"], capture_output=True, text=True)
devlist = result.stdout.splitlines()

result = subprocess.run(["xsetwacom", "get", device, function], capture_output=True, text=True)
data = result.stdout.replace("\n", "")
```

### 4. **修改的文件明細**

#### wacom_interface.py
- 替換 `os.popen()` → `subprocess.run()`
- 移除 `import os`，添加 `import subprocess`
- 更新字符串編碼/解碼

#### wacom_utility.py
- 更新 GTK 導入為 GI (gobject-introspection)
- 替換所有 `gtk.*` 調用為 `Gtk.*`
- 替換所有 `.get_widget()` → `.get_object()`
- 替換 `gtk.glade.XML()` → `Gtk.Builder()`
- 替換 `gtk.main()` → `Gtk.main()`

#### tablet_capplet.py
- 移除 `import pygtk` 和 `pygtk.require('2.0')`
- 添加 GI 導入
- 替換 `subprocess.Popen()` → `subprocess.run()`
- 替換所有 GTK 和 GDK API 調用
- 更新事件掩碼：`gtk.gdk.POINTER_MOTION_MASK` → `Gdk.EventMask.POINTER_MOTION_MASK`
- 替換 `gobject` → `GObject`
- 替換 `gtk.gdk.devices_list()` → `Gdk.display_get_default().list_devices()`

#### wacom_xorg.py
- 添加 `import subprocess`（用於未來改進）

#### wacom_identify.py
- 替換 `os.popen()` → `subprocess.run()`
- 更新行分割邏輯（`.splitlines()` 而非 `.readlines()`）

#### dialogbox.py
- 更新 GTK 導入為 GI
- 替換所有 `.get_widget()` → `.get_object()`
- 替換 `gtk.main_quit()` → `Gtk.main_quit()`

#### cairo_framework.py
- 更新 GTK 導入為 GI
- 替換 `gtk.DrawingArea` → `Gtk.DrawingArea`

#### wacom_data.py
- 無重大更改（xml.dom.minidom 在 Python 3 中仍然支持）

### 5. **依賴項更新**

#### 舊依賴（Python 2）：
```
pygtk
python-xml.dom.minidom
wacom-tools
```

#### 新依賴（Python 3）：
```
python3-gi
python3-gi-cairo
python3-xml.dom.minidom
wacom-tools
gir1.2-gtk-3.0
```

### 6. **已知兼容性問題與注意事項**

1. **GTK 3 Glade 文件**：`.glade` 文件需要是 GTK 3 兼容格式
2. **設備列表 API**：`gtk.gdk.devices_list()` 在 GTK 3 中已棄用，改用 `Gdk.display_get_default().list_devices()`
3. **字符串編碼**：Python 3 對字符串編碼更嚴格，所有子進程輸出使用 `text=True` 自動解碼

### 7. **測試建議**

- 測試設備識別功能
- 測試 Xorg 配置修改
- 測試 Wacom 設備設置應用
- 驗證 UI 渲染正確
- 確保壓力曲線和點擊力量設置工作

### 8. **後續改進建議**

1. 考慮遷移至 PyGObject/GTK 4（更現代）
2. 添加類型提示以改進代碼質量
3. 使用 `pathlib` 替代 `os.path` 操作
4. 改進錯誤處理（使用更具體的異常）
5. 添加單元測試

---
**遷移完成日期**：2026年3月6日
**Python 版本**：3.7+
**GTK 版本**：3.x
