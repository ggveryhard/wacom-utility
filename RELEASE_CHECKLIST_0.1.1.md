# 0.1.1 Release Checklist

## 1. Prepare Changes

1. Update code and docs.
2. Verify `packaging/rpm/wacom-utility.spec`:
   - `Version: 0.1.1`
   - `Release: 1%{?dist}`
   - `%changelog` has new `0.1.1-1` entry.
3. Verify desktop entry exists:
   - `packaging/rpm/wacom-utility.desktop`

## 2. Local Validation

1. Python syntax check:
```bash
python3 -m py_compile wacom_utility.py wayland_pad_daemon.py wacom_interface.py wacom_data.py cairo_framework.py
```

2. Spec lint/check:
```bash
rpmlint packaging/rpm/wacom-utility.spec
rpmspec -P packaging/rpm/wacom-utility.spec > /tmp/wacom-utility.spec.expanded
```

3. Optional local RPM build:
```bash
rpmbuild -ba packaging/rpm/wacom-utility.spec
```

## 3. Git + Tag

1. Commit:
```bash
git add .
git commit -m "Release 0.1.1"
```

2. Tag:
```bash
git tag -a v0.1.1 -m "v0.1.1"
git push origin master
git push origin v0.1.1
```

## 4. COPR Trigger

1. In COPR (`eyes1971/wacom-utility`), trigger build from updated source.
2. Confirm target chroots (e.g. `fedora-43-x86_64`).
3. Watch build logs until `succeeded`.

## 5. Post-build Install Test

1. Install from COPR:
```bash
sudo dnf copr enable eyes1971/wacom-utility
sudo dnf upgrade --refresh wacom-utility
```

2. Validate runtime:
```bash
wacom-utility --check
systemctl --user daemon-reload
systemctl --user restart wacom-wayland-pad-daemon.service
systemctl --user status wacom-wayland-pad-daemon.service
```

3. Functional regression smoke test:
- GUI opens and device list shows Pad/Pen
- Pad tab `Edit` dialog opens
- Wayland mapping writes `~/.wacom_utility_wayland.json`
- `wayland_pad_daemon.py` triggers mapped key/button
- Strip scroll works (`EV_ABS` path)

## 6. Release Notes (short)

Document:
- New features/fixes
- Packaging changes
- Known issues/workarounds
