# Wacom Utility - Python 3 升級檢查清單

## ✅ 已完成的升級項目

### 核心文件升級
- ✅ `wacom_utility.py` - 主應用程序文件
  - 更新 shebang 為 python3
  - 遷移 GTK 2 → GTK 3 (GI)
  - 替換所有 `os.popen()` 調用
  - 更新 glade XML 加載方式

- ✅ `wacom_interface.py` - Wacom 設備接口
  - 替換 `os.popen()` → `subprocess.run()`
  - 更新字符串處理

- ✅ `tablet_capplet.py` - 圖形平板小程序
  - 移除 `pygtk` 和 `gobject`
  - 遷移至 GTK 3 (GI)
  - 更新所有設備 API 調用
  - 替換 `subprocess.Popen()` → `subprocess.run()`

- ✅ `wacom_xorg.py` - Xorg 配置工具
  - 添加 subprocess 導入準備

- ✅ `wacom_identify.py` - 設備識別工具
  - 替換 `os.popen()` → `subprocess.run()`

- ✅ `dialogbox.py` - 對話框
  - 遷移至 GTK 3 (GI)
  - 更新小部件獲取方法

- ✅ `cairo_framework.py` - 繪圖框架
  - 遷移至 GTK 3 (GI)

- ✅ `wacom_data.py` - 設備數據
  - Python 3 兼容（無需改動）

## 📋 主要 API 變更速查表

### 1. 導入變更
```python
# 舊（Python 2）
import gtk
import gtk.glade
import gobject
import pygtk
pygtk.require('2.0')

# 新（Python 3）
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject
```

### 2. 主循環
```python
# 舊
gtk.main()
gtk.main_quit()

# 新
Gtk.main()
Gtk.main_quit()
```

### 3. 小部件獲取
```python
# 舊
builder = gtk.glade.XML("file.glade")
widget = builder.get_widget("widget_name")

# 新
builder = Gtk.Builder()
builder.add_from_file("file.glade")
widget = builder.get_object("widget_name")
```

### 4. 小部件創建
```python
# 舊
label = gtk.Label("text")
hbox = gtk.HBox()
button = gtk.Button(stock="gtk-edit")

# 新
label = Gtk.Label(label="text")
hbox = Gtk.HBox()
button = Gtk.Button(stock_id="gtk-edit")
```

### 5. 進程執行
```python
# 舊
output = os.popen("command arg1 arg2").read()
lines = os.popen("command").readlines()

# 新
result = subprocess.run(["command", "arg1", "arg2"], capture_output=True, text=True)
output = result.stdout
lines = result.stdout.splitlines()
```

### 6. 事件掩碼
```python
# 舊
self.set_events(gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.BUTTON_PRESS_MASK)

# 新
self.set_events(Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.BUTTON_PRESS_MASK)
```

### 7. 設備列表
```python
# 舊
devices = gtk.gdk.devices_list()

# 新
devices = Gdk.display_get_default().list_devices()
```

### 8. 超時
```python
# 舊
gobject.timeout_add(20, self.Update)

# 新
GObject.timeout_add(20, self.Update)
```

## 🚀 運行應用程序

### 安裝依賴
```bash
# Ubuntu/Debian
sudo apt-get install python3 python3-gi python3-gi-cairo gir1.2-gtk-3.0 wacom-tools

# Fedora/RHEL
sudo dnf install python3 python3-gobject gtk3 wacom-tools
```

### 運行應用
```bash
# 直接運行
python3 wacom_utility.py

# 或使用 shebang
./wacom_utility.py

# 配置模式
./wacom_utility.py --configure
# 或
./wacom_utility.py -c
```

## ⚠️ 可能的問題與解決方案

### 問題 1：找不到 GTK 3
```
ImportError: cannot import name 'Gtk' from gi.repository
```
**解決**：安裝 GTK 3 開發文件
```bash
# Ubuntu/Debian
sudo apt-get install libgtk-3-dev gir1.2-gtk-3.0

# Fedora
sudo dnf install gtk3-devel
```

### 問題 2：.glade 文件不兼容
```
GLib.Error: g-markup-error-quark: [error]
```
**解決**：確保 .glade 文件是 GTK 3 格式，可用 Glade 設計工具重新保存

### 問題 3：設備識別失敗
```
No graphics tablets detected
```
**解決**：
- 確保 `lsusb` 命令可用
- 檢查 Wacom 設備連接
- 驗證 xsetwacom 已安裝

### 問題 4：權限錯誤
```
PermissionError: [Errno 13] Permission denied
```
**解決**：某些操作需要管理員權限，使用 `gksu` 或 `sudo`

## 📝 測試檢查清單

- [ ] 應用程序啟動無錯誤
- [ ] 設備識別正確
- [ ] UI 元素正確呈現
- [ ] 壓力曲線設置可用
- [ ] 按鈕映射編輯功能
- [ ] Xorg 配置修改
- [ ] 設置保存/加載
- [ ] 自動啟動功能

## 📚 參考資源

- [GTK 3 官方文檔](https://developer.gnome.org/gtk3/stable/)
- [PyGObject 文檔](https://pygobject.readthedocs.io/)
- [Python subprocess 文檔](https://docs.python.org/3/library/subprocess.html)
- [Glade GTK 3](https://glade.gnome.org/)

---

**最後更新**：2026年3月6日
**Python 版本**：3.7+
**GTK 版本**：3.x
