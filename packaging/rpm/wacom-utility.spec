Name:           wacom-utility
Version:        0.1.3
Release:        1%{?dist}
Summary:        GTK4 Wacom utility with Wayland pad daemon

License:        GPL-2.0-only
URL:            https://github.com/ggveryhard/wacom-utility
# Source tarball from GitHub version tag.
Source0:        %{url}/archive/refs/tags/v%{version}.tar.gz#/%{name}-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  systemd-rpm-macros
BuildRequires:  python3
BuildRequires:  python3-devel
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
PYTHONPATH=src python3 -m py_compile \
    src/wacom_utility/__init__.py \
    src/wacom_utility/resources.py \
    src/wacom_utility/wacom_utility.py \
    src/wacom_utility/wayland_pad_daemon.py \
    src/wacom_utility/wacom_interface.py \
    src/wacom_utility/wacom_identify.py \
    src/wacom_utility/wacom_data.py \
    src/wacom_utility/wacom_xorg.py \
    src/wacom_utility/cairo_framework.py \
    src/wacom_utility/tablet_capplet.py \
    src/wacom_utility/dialogbox.py
cd src
%{__python3} -c "import wacom_utility"
cd ..
desktop-file-validate packaging/rpm/wacom-utility.desktop

%install
install -d %{buildroot}%{python3_sitelib}/wacom_utility
cp -a src/wacom_utility/* %{buildroot}%{python3_sitelib}/wacom_utility/

install -d %{buildroot}%{_bindir}
cat > %{buildroot}%{_bindir}/wacom-utility << 'EOF'
#!/usr/bin/bash
exec %{__python3} -m wacom_utility.wacom_utility "$@"
EOF
chmod 0755 %{buildroot}%{_bindir}/wacom-utility

cat > %{buildroot}%{_bindir}/wacom-wayland-pad-daemon << 'EOF'
#!/usr/bin/bash
exec %{__python3} -m wacom_utility.wayland_pad_daemon "$@"
EOF
chmod 0755 %{buildroot}%{_bindir}/wacom-wayland-pad-daemon

%{__python3} scripts/render-systemd-service.py \
    --template systemd/ydotoold.service.in \
    --output %{buildroot}%{_userunitdir}/ydotoold.service \
    --exec-start "/usr/bin/ydotoold --socket-path=%t/.ydotool_socket --socket-perm=0660"
chmod 0644 %{buildroot}%{_userunitdir}/ydotoold.service

%{__python3} scripts/render-systemd-service.py \
    --template systemd/wacom-wayland-pad-daemon.service.in \
    --output %{buildroot}%{_userunitdir}/wacom-wayland-pad-daemon.service \
    --unit-extra Wants=ydotoold.service \
    --unit-extra After=ydotoold.service \
    --service-extra Environment=YDOTOOL_SOCKET=%t/.ydotool_socket \
    --exec-start %{_bindir}/wacom-wayland-pad-daemon
chmod 0644 %{buildroot}%{_userunitdir}/wacom-wayland-pad-daemon.service
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
%{_userunitdir}/ydotoold.service
%{_userunitdir}/wacom-wayland-pad-daemon.service
%{_datadir}/applications/wacom-utility.desktop
%{python3_sitelib}/wacom_utility

%changelog
* Fri Mar 06 2026 ggveryhard <ggveryhard@users.noreply.github.com> - 0.1.3-1
- Restructure project into a PyPI-style src package with packaged resources
- Split user install and RPM/systemd service paths for ~/.local and /usr/bin
- Replace source-checkout service assumptions with entry point based execution
- Add pyproject metadata, package data, and user install documentation

* Fri Mar 06 2026 ggveryhard <ggveryhard@users.noreply.github.com> - 0.1.2-1
- Add Touch Strip apply/save flow in GTK4 UI
- Fix Wayland PTZ-630 button index mapping mismatch
- Separate strip_mappings from button mappings to avoid conflicts
- Remove non-functional ExpressKeys Layout block
- Simplify mapping dropdown labels to show only GUI button names

* Fri Mar 06 2026 ggveryhard <ggveryhard@users.noreply.github.com> - 0.1.0-1
- COPR-ready initial packaging
- Add runtime dependency details for GTK4/Wayland/X11 fallback
- Add %%check py_compile stage to reduce first-build failure risk
- Include migration/upgrade docs in package
- Add desktop entry for app launcher integration
