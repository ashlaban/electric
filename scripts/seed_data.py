"""Seed script to populate the database with sample data."""

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.db.models.meter import Meter, MeterType
from app.db.models.meter_reading import MeterReading
from app.db.models.property import Property
from app.db.models.user import User


async def seed_database() -> None:
    """Seed the database with sample data."""
    async with AsyncSessionLocal() as db:
        # Check if data already exists
        result = await db.execute(select(Property))
        if result.first():
            print("Database already has data. Skipping seed.")
            return

        print("Seeding database...")

        # Create a property
        property_obj = Property(
            name="Test Building",
            address="123 Main Street, Stockholm",
        )
        db.add(property_obj)
        await db.flush()

        print(f"Created property: {property_obj.name} (ID: {property_obj.id})")

        # Create meters
        total_meter = Meter(
            property_id=property_obj.id,
            meter_code="total",
            meter_type=MeterType.PHYSICAL_MAIN,
            description="Main meter - total consumption",
            unit="kWh",
        )
        gg_meter = Meter(
            property_id=property_obj.id,
            meter_code="gg",
            meter_type=MeterType.PHYSICAL_SUBMETER,
            description="GG circuit submeter",
            unit="kWh",
        )
        sg_meter = Meter(
            property_id=property_obj.id,
            meter_code="sg",
            meter_type=MeterType.PHYSICAL_SUBMETER,
            description="SG circuit submeter",
            unit="kWh",
        )
        unmetered_meter = Meter(
            property_id=property_obj.id,
            meter_code="unmetered",
            meter_type=MeterType.VIRTUAL,
            description="Unmetered consumption (total - gg - sg)",
            unit="kWh",
        )

        db.add_all([total_meter, gg_meter, sg_meter, unmetered_meter])
        await db.flush()

        print(f"Created 4 meters: total, gg, sg, unmetered")

        # Create sample users
        user1 = User(
            property_id=property_obj.id,
            name="John Doe",
            phone_number="+46701234567",
            default_meter_id=gg_meter.id,
        )
        user2 = User(
            property_id=property_obj.id,
            name="Jane Smith",
            phone_number="+46709876543",
            default_meter_id=sg_meter.id,
        )

        db.add_all([user1, user2])
        await db.flush()

        print(f"Created 2 users: {user1.name}, {user2.name}")

        # Create sample readings for the past 30 days
        base_date = datetime.now(timezone.utc) - timedelta(days=30)
        base_total = Decimal("10000.00")
        base_gg = Decimal("4000.00")
        base_sg = Decimal("3000.00")

        for day in range(31):
            reading_date = base_date + timedelta(days=day)

            # Simulate daily consumption
            daily_total = Decimal("15.00") + Decimal(day % 5)  # 15-20 kWh/day
            daily_gg = Decimal("6.00") + Decimal(day % 3)  # 6-9 kWh/day
            daily_sg = Decimal("4.50") + Decimal(day % 2)  # 4.5-6.5 kWh/day

            total_reading = MeterReading(
                meter_id=total_meter.id,
                reading_value=base_total + (daily_total * day),
                reading_timestamp=reading_date,
                created_by_user_id=user1.id if day % 2 == 0 else user2.id,
                notes=f"Day {day + 1} reading",
            )

            gg_reading = MeterReading(
                meter_id=gg_meter.id,
                reading_value=base_gg + (daily_gg * day),
                reading_timestamp=reading_date,
                created_by_user_id=user1.id,
                notes=f"Day {day + 1} reading",
            )

            sg_reading = MeterReading(
                meter_id=sg_meter.id,
                reading_value=base_sg + (daily_sg * day),
                reading_timestamp=reading_date,
                created_by_user_id=user2.id,
                notes=f"Day {day + 1} reading",
            )

            db.add_all([total_reading, gg_reading, sg_reading])

        await db.commit()

        print(f"Created 93 readings (31 days x 3 meters)")
        print("\nSeed data created successfully!")
        print(f"\nProperty ID: {property_obj.id}")
        print(f"Total Meter ID: {total_meter.id}")
        print(f"GG Meter ID: {gg_meter.id}")
        print(f"SG Meter ID: {sg_meter.id}")
        print(f"Unmetered Meter ID: {unmetered_meter.id}")
        print(f"\nYou can now calculate virtual readings for the unmetered meter.")


if __name__ == "__main__":
    asyncio.run(seed_database())
