# RPM Packaging Plan

This folder contains an initial RPM packaging skeleton:

- `wacom-utility.spec`
- `wacom-wayland-pad-daemon.service` (installed to user systemd unit dir)

## Build Prerequisites

Install build tools (Fedora example):

```bash
sudo dnf install rpm-build rpmdevtools systemd-rpm-macros
```

## Build Workflow

1. Create source tarball from project root:

```bash
VERSION=0.1.0
NAME=wacom-utility
cd /home/sam/Templates/SPEC
tar --exclude-vcs -czf ${NAME}-${VERSION}.tar.gz ${NAME}
```

2. Prepare rpmbuild tree:

```bash
rpmdev-setuptree
cp /home/sam/Templates/SPEC/wacom-utility/packaging/rpm/wacom-utility.spec ~/rpmbuild/SPECS/
cp /home/sam/Templates/SPEC/${NAME}-${VERSION}.tar.gz ~/rpmbuild/SOURCES/
```

3. Build:

```bash
rpmbuild -ba ~/rpmbuild/SPECS/wacom-utility.spec
```

Output RPMs:
- `~/rpmbuild/RPMS/noarch/wacom-utility-*.rpm`

## Notes

- Runtime data is installed to `/usr/share/wacom-utility`.
- Wrapper commands:
  - `/usr/bin/wacom-utility`
  - `/usr/bin/wacom-wayland-pad-daemon`
- User systemd unit is installed to `%{_userunitdir}`:
  - `wacom-wayland-pad-daemon.service`

After installation, user can enable daemon:

```bash
systemctl --user daemon-reload
systemctl --user enable --now wacom-wayland-pad-daemon.service
```
