Name:           wacom-utility
Version:        0.1.0
Release:        1%{?dist}
Summary:        GTK4 Wacom utility with Wayland pad daemon

License:        GPL-2.0-only
URL:            https://github.com/ggveryhard/wacom-utility
# Source tarball from GitHub version tag.
Source0:        %{url}/archive/refs/tags/v%{version}.tar.gz#/%{name}-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  systemd-rpm-macros
BuildRequires:  python3
BuildRequires:  desktop-file-utils

Requires:       python3
Requires:       python3-gobject
Requires:       python3-cairo
Requires:       python3-evdev
Requires:       gtk4
Requires:       ydotool
Recommends:     sway
Recommends:     xorg-x11-drv-wacom

%description
Wacom utility with GTK4 GUI and a Wayland daemon (evdev + ydotool).
Supports pad mapping workflow on Wayland and xsetwacom fallback on X11.

%prep
%autosetup -n %{name}-%{version}

%build
# no build step for pure Python project

%check
python3 -m py_compile \
    wacom_utility.py \
    wayland_pad_daemon.py \
    wacom_interface.py \
    wacom_identify.py \
    wacom_data.py \
    wacom_xorg.py \
    cairo_framework.py \
    tablet_capplet.py \
    dialogbox.py
desktop-file-validate packaging/rpm/wacom-utility.desktop

%install
install -d %{buildroot}%{_datadir}/%{name}

install -m 0644 wacom_utility.py %{buildroot}%{_datadir}/%{name}/wacom_utility.py
install -m 0644 wayland_pad_daemon.py %{buildroot}%{_datadir}/%{name}/wayland_pad_daemon.py
install -m 0644 wacom_interface.py %{buildroot}%{_datadir}/%{name}/wacom_interface.py
install -m 0644 wacom_identify.py %{buildroot}%{_datadir}/%{name}/wacom_identify.py
install -m 0644 wacom_data.py %{buildroot}%{_datadir}/%{name}/wacom_data.py
install -m 0644 wacom_xorg.py %{buildroot}%{_datadir}/%{name}/wacom_xorg.py
install -m 0644 cairo_framework.py %{buildroot}%{_datadir}/%{name}/cairo_framework.py
install -m 0644 tablet_capplet.py %{buildroot}%{_datadir}/%{name}/tablet_capplet.py
install -m 0644 dialogbox.py %{buildroot}%{_datadir}/%{name}/dialogbox.py
install -m 0644 keymap.txt %{buildroot}%{_datadir}/%{name}/keymap.txt
install -m 0644 wacom_utility_gtk4.ui %{buildroot}%{_datadir}/%{name}/wacom_utility_gtk4.ui
cp -a images %{buildroot}%{_datadir}/%{name}/

install -d %{buildroot}%{_bindir}
cat > %{buildroot}%{_bindir}/wacom-utility << 'EOF'
#!/usr/bin/bash
export WACOM_UTILITY_DATA_DIR=/usr/share/wacom-utility
exec /usr/bin/python3 /usr/share/wacom-utility/wacom_utility.py "$@"
EOF
chmod 0755 %{buildroot}%{_bindir}/wacom-utility

cat > %{buildroot}%{_bindir}/wacom-wayland-pad-daemon << 'EOF'
#!/usr/bin/bash
export WACOM_UTILITY_DATA_DIR=/usr/share/wacom-utility
exec /usr/bin/python3 /usr/share/wacom-utility/wayland_pad_daemon.py "$@"
EOF
chmod 0755 %{buildroot}%{_bindir}/wacom-wayland-pad-daemon

install -D -m 0644 packaging/rpm/wacom-wayland-pad-daemon.service \
    %{buildroot}%{_userunitdir}/wacom-wayland-pad-daemon.service
install -D -m 0644 packaging/rpm/wacom-utility.desktop \
    %{buildroot}%{_datadir}/applications/wacom-utility.desktop

%files
%license LICENSE
%doc README.md
%doc README_UPGRADE.md
%doc PYTHON3_MIGRATION.md
%doc UPGRADE_CHECKLIST.md
%doc UPGRADE_REPORT.md
%{_bindir}/wacom-utility
%{_bindir}/wacom-wayland-pad-daemon
%{_userunitdir}/wacom-wayland-pad-daemon.service
%{_datadir}/applications/wacom-utility.desktop
%{_datadir}/%{name}

%changelog
* Fri Mar 06 2026 ggveryhard <ggveryhard@users.noreply.github.com> - 0.1.0-1
- COPR-ready initial packaging
- Add runtime dependency details for GTK4/Wayland/X11 fallback
- Add %%check py_compile stage to reduce first-build failure risk
- Include migration/upgrade docs in package
- Add desktop entry for app launcher integration
