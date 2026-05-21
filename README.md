# Astrum-CubeSat---v1.26
A long-range LoRa-enabled 1U CubeSat prototype and ground station system featuring autonomous solar tracking, real-time gyroscope and environmental telemetry, and advanced fault-tolerant mechanisms for critical emergency response.

---

## Technical Architecture & Capabilities

### 1. Embedded Processing & Onboard Intelligence
* **Core Processing Unit:** Powered by the ESP32-S3 System-on-Chip (SoC), leveraging its dual-core architecture to decouple high-frequency sensor ingestion from communication scheduling.
* **Solar Tracking Subsystem:** Implements an autonomous biomimicry scanning routine that optimizes solar irradiance collection while mitigating mechanical wear.
  * **Scanning Routine:** Actuator sweeps are restricted to a calibrated $90^\circ$ safe window (between $45^\circ$ and $135^\circ$) to protect internal internal layout configurations and reduce motor strain.
  * **Lock-on State:** Upon detecting the peak lux threshold via localized light-dependent sensors, the system locks the solar arrays into a stable $180^\circ$ planar alignment to achieve maximum power efficiency.

### 2. Multi-Sensor Telemetry Pipeline
The satellite features a synchronized sensor array that samples physical parameters and structural physics at high frequency:
* **Attitude and Kinematics:** Integrated multi-axis gyroscope and accelerometer tracking to compute real-time pitch, roll, and angular velocity.
* **Environmental Diagnostics:** High-precision temperature and humidity tracking modules providing structural health diagnostics under varied thermal loads.

### 3. Aerospace Telecommunications & Telemetry Links
* **RF Transceiver Subsystem:** Driven by the AI-Thinker Ra-01SCHP module, integrating the Semtech LLCC68 sub-GHz chipset tuned to $433\text{ MHz}$.
* **Modulation & Range:** Operates on Chirp Spread Spectrum (CSS) modulation, boasting a robust **$151\text{ dB}$ Link Budget** ($22\text{ dBm}$ transmission power / $-129\text{ dBm}$ receiver sensitivity) to secure reliable Line-of-Sight (LoS) telemetry up to **$15\text{ km}$**.
* **Dual-Protocol Control Segment:**
  * **UDP Server Pipeline:** Dedicated high-speed packet ingestion for streaming live gyroscope arrays and instantaneous 3D orientation visualization on the Ground Station interface.
  * **TCP Control Link:** A secure, connection-oriented socket designed to dispatch critical command-and-control (C2) payloads, ensuring execution acknowledgment.

### 4. Fault Tolerance & Critical Fallback Mechanisms
To maintain subsystem integrity during operational anomalies, the firmware includes advanced fault-tolerant state-machines:
* **Emergency Isolation:** Automatically enters a low-power, safe-mode loop if telemetry links drop beyond critical timeouts or battery metrics degrade.
* **Command Overrides:** Supports absolute hardware-level overrides via the TCP command link, enabling remote operators to execute emergency system hard resets and diagnostic state rollbacks.
* **Data Security & Integrity:** Ingested packets are structured, verified through an Access Control List (ACL) layer, decrypted via AES-256 bit algorithms, and written directly into a local SQLite database architecture.

---

## Repository Structure

```text
├── hardware/           # Pinout configurations, circuit schematics, and 1U structural CAD models.
├── firmware/           # Production C++/ESP-IDF codebase for sensor drivers, tracking logic, and RF control.
├── ground-station/     # Python-based user interface, network socket infrastructure, and SQLite data logging.
├── docs/               # System architecture block diagrams, wiring layouts, and database schemas.
└── .gitignore          # Explicitly filters runtime databases (.db), compiled binaries, and IDE caches.
## Copyright & Legal Notice

**Copyright © 2026 Mohamed Salah Abd Elfatah Mohamed Ragab. All Rights Reserved.**

### ⚠️ WARNING & USAGE RESTRICTIONS
* **Strict Prohibition:** Reproduction, redistribution, modification, mirroring, or public/commercial usage of any code, schematics, or architectural designs in this repository is strictly prohibited without prior explicit, written authorization from the author.
* **Academic Integrity:** Any unauthorized copying, cloning, or plagiarism of this project for university graduation projects, conferences, or academic competitions will be met with immediate reporting to academic boards and copyright enforcement channels.
* **Inquiries & Permissions:** If you wish to request permission for academic research or collaborative development, you must contact the author directly via the verified channels provided below.
