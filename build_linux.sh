#!/usr/bin/env bash
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "=== [1/3] Sanal Ortam ve Bağımlılıklar Hazırlanıyor ==="
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install -r requirements.txt

echo "=== [2/3] PyInstaller ile Linux Binary Derleniyor ==="
python -m PyInstaller \
    --noconfirm \
    --clean \
    --noconsole \
    --name "elite-chess" \
    --paths . \
    --add-data "resources:resources" \
    main.py

echo "=== [3/3] Fedora/RHEL için .rpm Paketi Oluşturuluyor ==="
if command -v rpmbuild >/dev/null 2>&1; then
    mkdir -p build/rpmbuild/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
    mkdir -p dist/rpm
    rpmbuild \
        --define "_topdir $PROJECT_DIR/build/rpmbuild" \
        --define "project_root $PROJECT_DIR" \
        -bb packaging/rpm/elite-chess.spec
    
    cp build/rpmbuild/RPMS/x86_64/elite-chess-*.rpm dist/rpm/
    echo "✓ RPM Paketi oluşturuldu: $(ls -1 dist/rpm/elite-chess-*.rpm)"
else
    echo "UYARI: 'rpmbuild' bulunamadı, .rpm paketi atlandı."
fi

echo "=== Tamamlandı! ==="
echo "Binary: dist/elite-chess/elite-chess"
if [ -d "dist/rpm" ]; then
    echo "RPM Paketi: $(ls -1 dist/rpm/elite-chess-*.rpm 2>/dev/null || true)"
fi
