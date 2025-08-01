# 📹 CamTrack – Smart Device & Maintenance Management System

**CamTrack** is a comprehensive Django-based system designed for managing surveillance devices (or similar hardware), warehouses, maintenance processes, and coordination tasks efficiently. It enables organizations to monitor, track, and maintain device inventory across different warehouses and zones with full administrative control.

---

## 🚀 Features

### 🔐 Authentication & User Profile
- Login & logout system.
- View and manage user profiles.

### 📄 Contracts
- List all contracts.
- Add, edit, view, or delete a contract.
- Contracts are linked to warehouses.

### 🏬 Warehouses & Zones
- Manage multiple warehouses and their locations.
- View warehouse details, including related zones and device stats.

### 🖥 Devices
- Categorize devices by type.
- Add devices to warehouses and assign them to specific zones.
- Edit, delete, and change device status (installed, available, damaged).
- Import devices in bulk.
- Track IP address, responsible technician, transfer/installation dates, and notes.

### 🛠 Maintenance Cards
- Add maintenance reports per device.
- Track issues, repair dates, and technicians.
- Automatically update device status based on maintenance outcome.

### 📋 Tasks
- Manage internal tasks for team members.
- Add, update, delete tasks.
- Change task status dynamically.

### 📡 Coordination Requests
- Track and manage coordination requests.
- Add, edit, or delete coordination entries.

---

## 🧠 Tech Stack

- **Framework**: Django (Python)
- **Database**: SQLite / PostgreSQL / MySQL (depending on deployment)
- **Frontend**: Django Templates
- **Authentication**: Built-in Django Auth

---


