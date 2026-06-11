# CANRec — Car DVR + CAN/GPS Data Logger

A Raspberry Pi-based in-car recorder that captures **video**, **OBD-II/CAN data**, and
**GPS** on a common timeline. It shows a **live HUD** (speed, position, throttle/brake, RPM,
temps) on an in-car screen and serves **raw data + recordings** to a phone/laptop over Wi-Fi.

> Status: planning. This is a living document — we refine it as decisions get locked.

---

## 0. MVP scope (current focus)

**Front dashcam only**, because the OBD/CAN tap is the hard in-car wiring. Defer the rest until this works.

**In scope (MVP):**
- Buildroot fast-boot image (<10 s key-on → first recorded frame), read-only root.
- USB UVC camera, **1080p, Sony STARVIS low-light sensor** (good night vision priority) → loop-record segments to the SSD; save/lock trigger.
- Power from an **ACC/cigarette USB socket** + a **supercap UPS** that triggers a graceful shutdown on power loss (no fuse-tap hardwire yet).

**Deferred:** CAN HAT + OBD-II tap, fuse-tap hardwire + ignition-sense GPIO, live HUD + display, web companion.
**Easy fast-follow:** GPS (the M10 is in hand and needs no in-car wiring — can be added any time).

---

## 1. Goals *(full vision; MVP is §0)*

- **Dashcam**: continuous loop recording of clean video, with a "save/lock" trigger to protect a clip.
- **Live HUD**: real-time overlay on an in-car display — speed, GPS position, throttle/brake, RPM, temps.
- **Telemetry logging**: time-synced CAN + GPS captured for later analysis (track-day style).
- **Companion access**: connect a phone/laptop to the Pi's Wi-Fi and view live gauges + download raw data/video.

---

## 2. Key design decisions

| Decision | Choice | Rationale |
|---|---|---|
| Compute | **Raspberry Pi 4B+** (*owned*) | HW H.264 encode + decode at 1080p30 — can encode the camera's raw/MJPEG if it lacks onboard H.264. |
| OS | **Buildroot** custom minimal image | Only path that hits the **<10 s boot** goal; minimal & immutable by design. |
| Boot target | **<10 s (ideally <5 s) key-on → first recorded frame** | Hard constraint driving OS + camera choices. |
| Camera | **USB UVC, 1080p, Sony STARVIS low-light sensor** | Night vision priority (IMX462 best, IMX307 good). Onboard H.264, *or* MJPEG→Pi 4 HW H.264 encode. |
| OS model | **Read-only OS + writable data only** | Immutable root can't be corrupted by power loss; only the SSD data partition is written. |
| CAN access | **CANable 2.0** USB-CAN (SocketCAN) on OBD-II pins 6 & 14 | One interface does *both* PID polling (ISO-TP) *and* passive sniffing (brake/steering/blinkers). An **ELM327 can't sniff reliably** (see below). |
| Recording model | Clean video + timestamped data log; overlay rendered **live to screen**, not burned in | Low in-car compute; raw data stays pullable; burned-in overlay can be produced in post if wanted. |
| Data format | **MCAP** (or SQLite) | MCAP stores mixed timestamped streams and opens in Foxglove Studio with synced video+plots. |
| Time sync | One monotonic clock for all samples; **GPS PPS** disciplines absolute time via chrony | Makes overlay alignment and post-analysis trustworthy. |

### Locked
- ✅ Compute: Pi 4B+ · OS: Buildroot · Camera: USB UVC 1080p STARVIS low-light · GPS: Quescan M10 TTL-UART · CAN: CANable 2.0 (USB-CAN) on OBD-II pins.
- ✅ **MVP = front dashcam only** (record + fast boot + safe shutdown). CAN/OBD, fuse-tap hardwire, HUD, and web companion deferred until the dashcam works — see §0.

### Open decisions (to lock next)
- **USB camera model** — pick a **USB UVC** (not CSI/Pivariety) **Sony STARVIS 1080p** module — **IMX462** (best low light) or **IMX307** — with **WDR + auto IR-cut + fast lens (≤ f/1.6)**. Confirm whether it does onboard H.264 (path A) or needs Pi-side encode (path B). No IR LEDs (windshield glare).
- **Power/UPS** module choice (supercap hold time vs Pi 4 draw). For the MVP, power from an **ACC/cigarette USB socket** + a supercap UPS that triggers shutdown on input loss (no fuse-tap needed yet).
- **Display** size/type (deferred with the HUD).
- **Data format** — MCAP (Foxglove-friendly) vs SQLite (deferred with CAN/GPS logging).

---

## 3. Hardware (BOM)

| Part | Pick | Notes |
|---|---|---|
| Compute | **Raspberry Pi 4B+** (*owned*) | Buildroot custom image, read-only root. |
| Camera | **USB UVC, 1080p, Sony STARVIS** (IMX462 best / IMX307) | Night vision priority. WDR + auto IR-cut + fast lens (≤ f/1.6). Onboard H.264 *or* Pi 4 encodes the MJPEG. Must be USB UVC, **not** CSI/Pivariety. |
| Level shifter | Generic BSS138 (*owned*) | Only if M10 runs at 5V logic — see §6/§7. **Not** for the 12V sense. |
| **GPS** | **Quescan u-blox UBX-M10050 (NEO-M10), TTL-UART** — *owned* | See §6. Breaks out **PPS**. Wires straight to Pi UART. |
| CAN (final) | **CANable 2.0** (CAN-FD, `gs_usb`/candleLight) | ⭐ Pick. Native `can0`, **no SPI overlay** → easiest on Buildroot; lossless capture; does PID poll *and* sniff. ~$30–40. |
| CAN alt (HAT) | Waveshare **2-CH CAN-FD HAT (MCP2518FD)** | If you want HAT form factor / 2nd bus. Proper FIFOs (unlike MCP2515). Needs device-tree overlay. **Avoid plain MCP2515 HATs** — RX overflow on busy buses. |
| CAN alt (premium) | PEAK **PCAN-USB FD** | Industrial, bulletproof, `peak_usb` mainline. ~$200+, overkill but flawless. |
| OBD cable | **OBD-II → DB9** | OBD 6→CAN-H, 14→CAN-L, 4/5→GND → DB9 7=CAN-H, 2=CAN-L, 3=GND. (Or CANable screw-terminal + bare leads.) |
| OBD (prototype) | **Vgate iCar Pro 2S** ELM327 BT (*owned*) | ✅ standard PIDs via `python-OBD`, no purchase. ❌ can't sniff raw frames / do brake RE. Dev tool, replaced by the CANable in the final build. |
| Storage | USB SSD (or NVMe in a USB enclosure — Pi 4 has no PCIe) | Not microSD for continuous logging (endurance + power-loss corruption). |
| Display | 5–7" DSI/HDMI touchscreen | The live HUD. |
| Power | 12V→5V/5A buck + ignition-sense + supercap/UPS HAT | Clean shutdown on ignition-off is **mandatory**. |
| Enclosure | Vented, heat-tolerant | Parked cabin can hit 60–80°C. |

---

## 4. Architecture

```
        ┌──────────── Raspberry Pi (Linux) ────────────┐
Camera ─┤ capture ─┐                                    │
        │          ├─► timestamper (1 common clock) ─┬─► storage
GPS   ──┤ gpsd ────┤                                  │   • video: H.264 segments (loop-record)
        │          │                                  │   • data:  MCAP / SQLite (CAN+GPS)
OBD/CAN ┤ SocketCAN┘                                  │
        │                                             ├─► live HUD  → HDMI/DSI screen
        │                                             └─► web server → Wi-Fi AP → phone/laptop
        └───────────────────────────────────────────────┘
            power: 12V→5V buck + ignition-sense + safe-shutdown UPS
```

---

## 5. Software components (Python-friendly)

1. **Acquisition** — `python-can` + `cantools` (DBC decode) over SocketCAN; `gpsd` + `gpsd-py3` for GPS;
   **V4L2/UVC** for the USB camera — grab onboard H.264, *or* grab MJPEG and encode via the Pi 4 HW
   encoder (`v4l2h264enc`). No libcamera/picamera2.
2. **Timestamping** — every CAN frame, GPS fix, and video frame (PTS) tagged to one monotonic clock;
   `chrony` + GPS PPS for absolute time.
3. **Storage** — segmented H.264 video (1–5 min) with loop-delete-oldest + save/lock trigger; data in MCAP/SQLite.
4. **Live HUD** — renders straight to **DRM/KMS** (no desktop/X — keeps boot fast): GStreamer `kmssink`
   for the preview stream + a lightweight overlay (SDL2 / OpenGL ES / Cairo) compositing telemetry.
5. **Companion server** — FastAPI + WebSocket for live gauges; download endpoints; Pi as Wi-Fi AP (hostapd).
6. **Orchestration** — **minimal init** (BusyBox/runit — *not* systemd, which fights the <10 s boot goal):
   launch the recorder as the primary userland process, watchdog, power-loss → flush + shutdown.

### Signals available
- **OBD-II PIDs (easy, identical on all makes):** RPM `0x0C`, speed `0x0D`, coolant temp `0x05`, throttle/accel pedal `0x11`/`0x49`–`0x4B`, MAF, etc. Toyota powertrain CAN: typically **500 kbps, 11-bit IDs**.
- **Raw CAN only (needs DBC):** ⚠️ **brake pedal status is not a standard OBD PID** — it lives on the raw bus as a manufacturer-specific message. This is the main reason for the CAN-HAT approach.
- **🚗 Vehicle: 2024 Toyota Fortuner** — IMV **body-on-frame** platform, shares architecture with the **Hilux**; **not** a TNGA unibody car; **not** an openpilot-supported model.
  - **No ready-made Fortuner DBC** (not sold in openpilot's markets) — but *not* starting from zero:
    - **Standard OBD-II PIDs work regardless** (RPM, speed, coolant, throttle) — basics are free, no DBC.
    - Toyota reuses signal definitions, so opendbc's **generic Toyota powertrain DBC + any Hilux** CAN work is a strong starting point; expect a chunk of frames to decode, then fill gaps.
  - **Reverse-engineer the gaps** (e.g. brake pedal) — RE recipe (stationary, safe):
    1. **Gateway check first:** `candump` at 500 kbps and confirm lots of *broadcast* frames appear (not just diagnostic replies). If quiet until polled → gateway → brake likely not visible at OBD.
    2. **Cut noise:** ignition ON, **engine OFF**, hands off everything else.
    3. **Repeat the action:** log one continuous `candump -l` while doing *idle → press → release* ~5–10× in rhythm.
    4. **Analyze in SavvyCAN / cabana:** scrub the timeline; find the bit/byte that flips in sync with every press. Ignore always-changing **rolling counters / checksum** bytes (false positives).
    - Brake **on/off** (switch bit) = easy, one session. Brake **pressure** (analog) = separate, harder signal.
  - ⚠️ A 2024 model *may* include a security/OBD gateway limiting passive visibility at the port — the gateway check above tells you.

- **CAN adapter setup (CANable 2.0 / any `gs_usb` board, incl. 3D-printer/Klipper U2C-type):**
  1. Firmware = **candleLight (`gs_usb`)** → native `can0` (not slcan).
  2. ⚠️ **Disable the 120Ω termination** jumper/bridge — a vehicle OBD bus is already terminated (~60Ω); a third terminator skews impedance.
  3. Bitrate **500000** (classical CAN). Bring-up: `ip link set can0 type can bitrate 500000 && ip link set can0 up`, then `candump can0`.

---

## 6. GPS module — Quescan UBX-M10050 (NEO-M10) integration

- **Chip:** u-blox UBX-M10050, multi-GNSS concurrent (GPS, GLONASS, Galileo, BeiDou, QZSS + SBAS), TCXO, onboard flash (config persists). ~1.5 m CEP.
- **Variant:** ✅ **TTL-UART** (confirmed) — no level converter needed.
- **Wiring (6 pins):** EN (enable), GND, RX, TX, VCC (3.3–5V), **PPS**.
  - Connect to Pi: module **TX → Pi GPIO15 (RXD, pin 10)**, module **RX → Pi GPIO14 (TXD, pin 8)** (crossed), GND→GND.
  - **Logic levels:** power the module from **3.3V** so its I/O is ≤3.3V → wire straight to the Pi, no shifter. If run at 5V and its TX swings 5V, put the (owned) BSS138 shifter inline (HV=5V, LV=3.3V, common GND) — fine at 115200. Or use a USB-UART adapter to keep the Pi's UART free.
  - Disable the Linux serial console and enable the UART (`raspi-config` → Interface → Serial: login shell *off*, hardware *on*) so the port is free for gpsd.
  - Wire **PPS** to a spare Pi GPIO and enable the kernel `pps-gpio` overlay for chrony time discipline.
- **Configure (one-time, persists to flash):**
  - Raise nav rate from default **1 Hz → 10 Hz** (M10 supports higher; 10 Hz is the track-logging sweet spot).
  - Raise baud **9600 → 115200** (9600 can't carry 10 Hz NMEA reliably).
  - Optionally enable **UBX-NAV-PVT** (single binary message with position/velocity/time) instead of multi-sentence NMEA.
  - Tools: u-center 2 (Windows), `pygpsclient`, or `pyubx2` (send `CFG-VALSET`) from the Pi.
- **Software:** register with **gpsd**; read via `gpsd-py3`. PPS via `gpsd`/`chrony` + kernel PPS.
- **Antenna:** for a car, use/position the antenna with clear sky view (dash near windshield or roof) for fast fix + accuracy.
- **TODO:** confirm default baud/rate on first boot; decide NMEA vs UBX.

---

## 7. OS, immutability & safe shutdown

**Core principle: read-only OS, writable data only.** The root filesystem is read-only so power
loss cannot corrupt it. The *only* thing written at runtime is the video/telemetry data partition
on the SSD. Recording in short, fsync'd segments + a brief UPS hold = a clean close on shutdown.
Bonus: a read-only root means the SD/boot media isn't worn out by writes.

### Hard constraint: **insanely fast boot (<10 s, ideally <5 s) to first recorded frame.**
The real metric is *key-on → first recorded video frame*, not boot-to-login. Buildroot launches our
recorder as effectively the only userland process, so that gap is small.

| Option | Boot to app | Immutability | Camera | Effort |
|---|---|---|---|---|
| **Buildroot / Yocto** (custom image) | **~3–6 s** ✅ | Minimal & immutable by design | Must integrate the camera stack (see below) | High |
| Raspberry Pi OS Lite + overlay root | ~12–20 s (≈10 s if heavily trimmed) ❌ | Read-only root, RAM overlay | ✅ libcamera/picamera2 first-class | Low |
| Ubuntu Core / balenaOS | 20–40 s+ ❌ | Truly immutable, OTA | ⚠️ extra work | Medium |

**Decision: Buildroot** — the only path that reliably hits <10 s. (Also tune the Pi firmware:
disable boot splash/`boot_delay`, USB/network boot probing.)

**Camera: ✅ USB UVC, 1080p, Sony STARVIS low-light sensor (chosen).** No libcamera/ISP in the image
(USB UVC, not CSI) — keeps the fast-boot Buildroot path tractable. Night vision priority drives the
sensor: **IMX462** (best low light) or **IMX307**; want **WDR**, **auto IR-cut**, fast lens (≤ f/1.6),
and **no IR LEDs** (they reflect off the windshield). Two encode paths at 1080p:
- **A — onboard H.264/H.265:** grab-and-write over V4L2. Lowest bandwidth/effort.
- **B — MJPEG/raw out:** encode on the **Pi 4 HW H.264 encoder** (`v4l2h264enc`, 1080p30). Unlocks the
  best IMX462 modules that lack onboard encode.

*(Rejected: Camera Module 3 (CSI) — better sensor but needs libcamera + ISP tuning in the image;
and any IMX462 "Pivariety"/CSI module, which is MIPI not USB.)*

### Power & ignition sense

**MVP (simplest, no fuse-tap):** power the Pi from an **ACC/cigarette USB socket** (cuts with the key)
through a **supercap UPS**. The UPS detects its own input loss → signals the Pi → graceful shutdown.
No separate sense GPIO, no fuse-box wiring.

**Full hardwire (later — "fuse tap"):**
- Add-a-fuse at the fuse box on a **switched/ignition (ACC) circuit** → 12V live with the key on, dead when off.
- Power the Pi from it via a 12→5V/≥3A buck; the supercap/UPS holds the Pi ~15–30 s after key-off. No parasitic drain when parked.
- **Sense:** detect switched-12V presence on a GPIO via an **optocoupler or voltage divider**.
  ⚠️ **Never feed 12V to a 3.3V GPIO, and a generic logic level shifter is NOT rated for 12V** — it tops out ~5V.

**Shutdown daemon (both cases):** on power-loss/ignition-off → stop recording → close & **fsync**
current segment → `poweroff`, all before the supercap drains.

### Write-hardening
- Video in **1–5 min segments**, each closed + fsync'd; loop-delete oldest; save/lock trigger to protect a clip.
- Data partition: journaled fs (ext4 or f2fs) mounted with safe options; **swap disabled**; writes minimized.
- Everything else (root, boot) read-only.

---

## 8. Phased build plan

**MVP (front dashcam):**
- **Phase 0 — Foundations:** build minimal Buildroot image (read-only root) + boot tuning, **measure key-on→app**, repo scaffold, dev env.
- **Phase 1 — Camera capture:** grab the 2K H.264 stream over V4L2; loop-record fsync'd segments to the SSD; save/lock trigger.
- **Phase 2 — Safe shutdown:** supercap UPS + power-loss detection → stop recording → close & fsync segment → `poweroff`. Field-test the full dashcam in the car (ACC USB power).

**Fast-follow:**
- **Phase 3 — GPS:** M10 via gpsd (in hand, no car wiring); log fixes + PPS time discipline.

**Deferred (the hard wiring / full vision):**
- **Phase 4 — CAN/OBD:**
  - **4a (now, free):** PID prototyping with the **Vgate iCar Pro 2S** over `python-OBD` — RPM/speed/coolant/throttle; confirms the car answers PIDs.
  - **4b (needs wired interface):** USB-CAN/HAT on OBD-II pins + fuse-tap + ignition-sense GPIO; passive sniff + PID poll; decode with the **Toyota `opendbc` DBC**. First step: `candump` at 500 kbps to see what's broadcast for this model/year (the gateway check).
- **Phase 5 — Unified logger:** all streams → disk on a common clock (MCAP/SQLite).
- **Phase 6 — Live HUD** on display.
- **Phase 7 — Companion app:** Wi-Fi AP + web dashboard, session list, download, playback.
- **Phase 8 — Post tooling:** Foxglove layout and/or burned-in overlay export (RaceRender-style).

---

## 9. Risks / gotchas
- **Brake pedal needs raw CAN + DBC**, not OBD PIDs.
- **OBD PID polling is rate-limited** (a few Hz total); prefer passive sniffing for high-rate signals.
- **Power-loss filesystem corruption** is the #1 killer of DIY loggers — UPS/safe-shutdown is not optional.
- **Heat** in a parked car; **GPS cold-start** delay; **local laws** on windshield mounting / recording.

---

## 10. Next steps
1. **Prove the boot target first** — stand up a minimal Buildroot image for Pi 4 (read-only root, USB-SSD
   data partition), tune firmware (no splash/`boot_delay`/probing), and measure key-on → app. De-risks the whole project.
2. Bench-test the M10: wire TTL-UART to the Pi, free the UART, get a fix via gpsd. *(GPS in hand — natural starting point.)*
3. Source a **USB H.264 UVC cam** (confirm simultaneous H.264 + MJPEG) and a **supercap/UPS** module.
4. Scaffold the repo (Buildroot external tree + acquisition / storage / hud / web / init) and start Phase 1.
