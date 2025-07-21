# exec(open("contracts/seed_contracts.py", encoding="utf-8").read())
from contracts.models import Contract, DeviceCategory, ContractItem, Warehouse, Zone, Device
from datetime import date, timedelta
import random

# حذف البيانات القديمة (اختياري أثناء التطوير)
Device.objects.all().delete()
Zone.objects.all().delete()
Warehouse.objects.all().delete()
ContractItem.objects.all().delete()
Contract.objects.all().delete()
DeviceCategory.objects.all().delete()

# ✅ 1. إنشاء الأصناف
CATEGORY_CHOICES = [
    ('CAMERA_DOME', 'Camera - Dome'),
    ('CAMERA_BULLET', 'Camera - Bullet'),
    ('CAMERA_PTZ', 'Camera - PTZ'),
    ('CAMERA_LPR', 'Camera - LPR'),
    ('CAMERA_PANORAMIC', 'Camera - Panoramic'),
    ('NVR', 'NVR'),
    ('SWITCH', 'Switch'),
    ('CABLES', 'Cables'),
    ('RACK', 'Rack'),
    ('MONITOR', 'Monitor'),
    ('WORKSTATION', 'Work Station'),
    ('VIDEOWALL', 'Video Wall'),
    ('FIREALARM', 'Fire Alarm'),
]

category_objs = []
for code, label in CATEGORY_CHOICES:
    obj = DeviceCategory.objects.create(name=label)
    category_objs.append(obj)

# ✅ 2. إنشاء 3 عقود
for i in range(1, 4):
    contract = Contract.objects.create(
        contract_number=f"C-{100+i}",
        name=f"Contract {i}",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=365),
        notes=f"This is contract number {i}"
    )

    # ✅ 3. إنشاء مخزن مرتبط بالعقد
    warehouse = Warehouse.objects.create(
        name=f"Warehouse {i}",
        location=f"Location {i}",
        contract=contract
    )

    # ✅ 4. إنشاء مناطق مرتبطة بالعقد
    zones = []
    for j in range(1, 4):  # 3 مناطق لكل عقد
        zone = Zone.objects.create(
            name=f"Zone {i}-{j}",
            contract=contract,
            notes=f"Zone {j} for contract {i}"
        )
        zones.append(zone)

    # ✅ 5. إضافة أصناف إلى العقد
    for cat in random.sample(category_objs, 5):
        ContractItem.objects.create(
            contract=contract,
            category=cat,
            quantity=random.randint(5, 20),
            notes="Auto-generated item"
        )

    # ✅ 6. إنشاء أجهزة مرتبطة بالمخزن والمناطق
    for k in range(1, 16):  # 15 جهازًا لكل عقد
        cat = random.choice(category_objs)
        location = random.choice(['warehouse', 'zone'])
        zone = random.choice(zones) if location == 'zone' else None
        device = Device.objects.create(
            serial_number=f"D-{i}{k:02d}",
            name=f"{cat.name} {k}",
            invoice_number=f"INV-{i}{k:02d}",
            device_category=cat,
            warehouse=warehouse,
            current_location=location,
            zone=zone,
            status=random.choice(['installed', 'available', 'damaged']),
            ip_address="192.168.1." + str(random.randint(1, 254)),
            responsible_person=f"Tech {k}",
            transfer_date=date.today(),
            installation_date=date.today(),
            notes="Sample device"
        )

print("✅ Data seeding completed.")
