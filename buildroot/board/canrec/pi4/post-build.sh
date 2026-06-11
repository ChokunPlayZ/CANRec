#!/bin/sh
set -eu

BOARD_DIR="$(dirname "$(realpath "$0")")"

# ── Boot files → BINARIES_DIR flat layout (genimage inputpath) ───────────────
cp "$BOARD_DIR/config.txt"   "$BINARIES_DIR/"
cp "$BOARD_DIR/cmdline.txt"  "$BINARIES_DIR/"
cp "$BOARD_DIR/genimage.cfg" "$BINARIES_DIR/"

# Flatten Pi 4 firmware so genimage places them at the FAT root — don't rely
# on genimage's path-stripping of rpi-firmware/* entries.
cp    "$BINARIES_DIR/rpi-firmware/start4.elf"  "$BINARIES_DIR/"
cp    "$BINARIES_DIR/rpi-firmware/fixup4.dat"  "$BINARIES_DIR/"
cp -r "$BINARIES_DIR/rpi-firmware/overlays"    "$BINARIES_DIR/"

# ── Read-only root prep ───────────────────────────────────────────────────────
# /var/run must be a symlink to /run (tmpfs) so runtime PID/socket files land
# on RAM; same for /var/tmp.  rsync can't replace a directory with a symlink,
# so we do it here after the overlay has been applied.
rm -rf  "$TARGET_DIR/var/run"
ln -sf  /run "$TARGET_DIR/var/run"

rm -rf  "$TARGET_DIR/var/tmp"
ln -sf  /tmp "$TARGET_DIR/var/tmp"

# /etc/resolv.conf written by udhcpc must survive on the read-only root by
# redirecting through a tmpfs symlink.
rm -f   "$TARGET_DIR/etc/resolv.conf"
ln -sf  /tmp/resolv.conf "$TARGET_DIR/etc/resolv.conf"

# ── Web root permissions ──────────────────────────────────────────────────────
chmod 755 "$TARGET_DIR/var/www/cgi-bin/status.cgi"

# ── Ensure /run mount-point directory exists ─────────────────────────────────
mkdir -p "$TARGET_DIR/run"

# ── brcmfmac WiFi firmware (Pi 4 BCM43455) ───────────────────────────────────
# Copy from the already-extracted brcmfmac-sdio-firmware-rpi Buildroot package
# rather than re-downloading; avoids network access in post-build.
BRCM_DIR="$TARGET_DIR/lib/firmware/brcm"
mkdir -p "$BRCM_DIR"
if [ ! -f "$BRCM_DIR/brcmfmac43455-sdio.bin" ]; then
    BUILD_DIR="$(dirname "$BINARIES_DIR")/build"
    BRCM_PKG=$(ls -d "$BUILD_DIR"/brcmfmac_sdio-firmware-rpi-* 2>/dev/null | head -1)
    if [ -n "$BRCM_PKG" ]; then
        for fw in brcmfmac43455-sdio.bin brcmfmac43455-sdio.clm_blob brcmfmac43455-sdio.txt; do
            src=$(find "$BRCM_PKG" -name "$fw" 2>/dev/null | head -1)
            [ -n "$src" ] && cp "$src" "$BRCM_DIR/" || echo "WARNING: $fw not found in package" >&2
        done
    else
        echo "WARNING: brcmfmac-sdio-firmware-rpi build dir not found — WiFi firmware missing" >&2
    fi
fi

# ── Regenerate modules.dep ────────────────────────────────────────────────────
# Buildroot's kernel install runs depmod but xz-compressed .ko.xz modules can
# produce an incomplete modules.dep; run it again here after all packages land.
KVER=$(ls "$TARGET_DIR/lib/modules/" 2>/dev/null | head -1)
if [ -n "$KVER" ]; then
    "$HOST_DIR/sbin/depmod" -a -b "$TARGET_DIR" \
        -F "$BINARIES_DIR/System.map" "$KVER" 2>/dev/null || true
fi
