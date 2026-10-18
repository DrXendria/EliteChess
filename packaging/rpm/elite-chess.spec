Name:           elite-chess
Version:        1.0.0
Release:        3%{?dist}
Summary:        Elite Chess Tournament Manager
License:        GPL-3.0-or-later
URL:            https://github.com/DrXendria/EliteChess

%define _build_id_links none
%define debug_package %{nil}
%global __requires_exclude_from ^/opt/elite-chess/.*$
%global __provides_exclude_from ^/opt/elite-chess/.*$

%description
Elite Chess is a professional, FIDE-compliant chess tournament manager
with modern UI and Dutch-Swiss pairing engine.

%install
mkdir -p %{buildroot}/opt/elite-chess
mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}/usr/share/applications
mkdir -p %{buildroot}/usr/share/icons/hicolor/256x256/apps

# Copy bundled application
cp -a %{project_root}/dist/elite-chess/* %{buildroot}/opt/elite-chess/

# Create symlink in /usr/bin
ln -sf /opt/elite-chess/elite-chess %{buildroot}/usr/bin/elite-chess

# Install desktop file
install -m 644 %{project_root}/packaging/elite-chess.desktop %{buildroot}/usr/share/applications/elite-chess.desktop

# Install icon
install -m 644 %{project_root}/resources/logo.png %{buildroot}/usr/share/icons/hicolor/256x256/apps/elite-chess.png

%files
/opt/elite-chess
/usr/bin/elite-chess
/usr/share/applications/elite-chess.desktop
/usr/share/icons/hicolor/256x256/apps/elite-chess.png
