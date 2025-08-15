# Aquaponics Sensor Project — Shopping Checklist

Use this checklist to load carts quickly. Copy/paste the **SKU / Product ID** into each store’s search if a link changes.

---

## Mouser (Sensors + ADC + Resistor)
Add **qty 1** each unless noted.

- [ ] **DFRobot Gravity pH Sensor Kit V2** — *SEN0161-V2*  
      Notes: pH probe + interface board. Calibrate with pH 7 & pH 4 buffers.
- [ ] **DFRobot Gravity TDS Sensor/Meter** — *SEN0244*  
      Notes: Analog EC/TDS board + waterproof probe.
- [ ] **DFRobot Gravity ADS1115 16‑bit I²C ADC Module** — *DFR0553*  
      Notes: Reads analog pH/TDS via I²C on the Pi.
- [ ] **DFRobot Waterproof DS18B20 Temperature Probe** — *DFR0198*  
      Notes: Digital 1‑Wire temperature sensor.
- [ ] **Resistor 4.7 kΩ, 1/4 W, 1% (metal film, through‑hole)** — e.g., *KOA Speer MF1/4CCT52R4701F*  
      Qty: **2–5** (spares) • Notes: Pull‑up for DS18B20 (data ↔ 3.3 V). Any brand is fine.

**Optional (only if adding Dissolved Oxygen):**  
- [ ] **DFRobot Gravity Analog DO Kit** — *SEN0237-A* (wire to ADS1115 A2).

---

## Adafruit (Raspberry Pi + Power + Wiring)
Add **qty 1** each unless noted.

- [ ] **Raspberry Pi 4 Model B (4 GB)** — *Adafruit PID 4292*
- [ ] **Official Raspberry Pi USB‑C Power Supply (5.1 V / 3 A)**
- [ ] **Micro‑HDMI → HDMI Cable** (1–2 m)
- [ ] **MicroSD card 32 GB (A1/A2)**
- [ ] **Raspberry Pi 4 Case** (official or ventilated)
- [ ] **(Optional) Official Pi 4 Case Fan + Heatsink kit**
- [ ] **Half‑size solderless breadboard (400 pts)** — *Adafruit PID 64*
- [ ] **Premium jumper wires, Female↔Male, 6″ (20‑pack)** — *Adafruit PID 1953/1954*  
      Qty: **2 packs**

*(If your computer lacks a card slot)*  
- [ ] **USB microSD card reader**

---

## Amazon (Calibration Solutions)
Pick one **pH set** and one **TDS/EC point**.

**pH buffers** (choose 2‑pack with **pH 7.00** & **pH 4.00**)  
- [ ] Biopharm / Apera / Hanna — “pH 4 and 7 buffer, 250 mL”

**TDS / EC standard** (choose **one** of these)  
- [ ] **1413 µS/cm** conductivity standard (KCl) — 250 mL bottle  
- [ ] **342 ppm NaCl** TDS standard — bottle or sachets

> We’ll set your logger’s `TDS_MULTIPLIER` for the standard you pick (NaCl “0.5” scale vs KCl “~0.7” scale).

---

## Post‑Purchase Quick Setup Notes

- **Wiring:** pH→ADS **A0**, TDS→ADS **A1**, DS18B20 on **GPIO4** with **4.7 kΩ** pull‑up to 3.3 V. ADS1115 on I²C (**SDA=GPIO2**, **SCL=GPIO3**).
- **Pi prep:** enable **I²C** and **1‑Wire** in `raspi-config`. Install Python deps from `requirements.txt`.
- **Data retention:** set `WINDOW_DAYS=60` in your cron env so 30‑day daily‑average charts stay full.
- **Calibration:** pH (two‑point: 7.00 then 4.00). TDS: use your chosen standard; we’ll tune `TDS_MULTIPLIER` to match.

---

## Order Tracking (fill in as you buy)

| Store   | Item                                   | SKU / PID            | Qty | Price | Order # | Status |
|---------|----------------------------------------|----------------------|-----|-------|---------|--------|
| Mouser  | DFRobot pH Kit V2                      | SEN0161-V2           | 1   |       |         |        |
| Mouser  | DFRobot TDS Sensor                     | SEN0244              | 1   |       |         |        |
| Mouser  | DFRobot ADS1115 I²C ADC                | DFR0553              | 1   |       |         |        |
| Mouser  | DFRobot DS18B20 Probe                  | DFR0198              | 1   |       |         |        |
| Mouser  | Resistor 4.7 kΩ 1/4W 1%                | MF1/4CCT52R4701F     | 5   |       |         |        |
| Adafruit| Raspberry Pi 4 Model B (4 GB)          | 4292                 | 1   |       |         |        |
| Adafruit| Official Pi 4 USB‑C Power Supply       | —                    | 1   |       |         |        |
| Adafruit| Micro‑HDMI → HDMI cable                | —                    | 1   |       |         |        |
| Adafruit| 32 GB microSD (A1/A2)                  | —                    | 1   |       |         |        |
| Adafruit| Pi 4 Case                              | —                    | 1   |       |         |        |
| Adafruit| (Opt) Case Fan + Heatsink              | —                    | 1   |       |         |        |
| Adafruit| Half‑size breadboard                   | 64                   | 1   |       |         |        |
| Adafruit| Jumper wires F↔M 6″ (20‑pack)          | 1953 / 1954          | 2   |       |         |        |
| Amazon  | pH 7.00 buffer                         | —                    | 1   |       |         |        |
| Amazon  | pH 4.00 buffer                         | —                    | 1   |       |         |        |
| Amazon  | 1413 µS/cm OR 342 ppm standard         | —                    | 1   |       |         |        |

