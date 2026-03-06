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
VERSION=0.1.3
NAME=wacom-utility
PROJECT_ROOT=/path/to/${NAME}
cd "$(dirname "${PROJECT_ROOT}")"
tar --exclude-vcs -czf ${NAME}-${VERSION}.tar.gz "$(basename "${PROJECT_ROOT}")"
```

If you use the default spec `Source0` (GitHub tags), create and push tag first:

```bash
git tag -a v0.1.3 -m "v0.1.3"
git push origin v0.1.3
```

2. Prepare rpmbuild tree (local tarball flow):

```bash
rpmdev-setuptree
cp ${PROJECT_ROOT}/packaging/rpm/wacom-utility.spec ~/rpmbuild/SPECS/
cp "$(dirname "${PROJECT_ROOT}")"/${NAME}-${VERSION}.tar.gz ~/rpmbuild/SOURCES/
```

3. Build:

```bash
rpmbuild -ba ~/rpmbuild/SPECS/wacom-utility.spec
```

Output RPMs:
- `~/rpmbuild/RPMS/noarch/wacom-utility-*.rpm`

## Notes

- Python package is installed to `%{python3_sitelib}/wacom_utility`.
- Wrapper commands:
  - `%{_bindir}/wacom-utility`
  - `%{_bindir}/wacom-wayland-pad-daemon`
- User systemd unit is installed to `%{_userunitdir}`:
  - `wacom-wayland-pad-daemon.service`

After installation, user can enable daemon:

```bash
systemctl --user daemon-reload
systemctl --user enable --now wacom-wayland-pad-daemon.service
```
