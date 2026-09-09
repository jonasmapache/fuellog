"""SQLAlchemy models: users, app settings, vehicles, stations, fuel entries."""
from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class AppSettings(Base):
    """Single-row table (id == 1) holding instance-wide preferences."""

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)

    default_language: Mapped[str] = mapped_column(String(5), default="en")
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")

    currency_code: Mapped[str] = mapped_column(String(8), default="EUR")
    currency_symbol: Mapped[str] = mapped_column(String(8), default="€")
    currency_position: Mapped[str] = mapped_column(String(6), default="after")  # 'before' | 'after'

    default_fuel_type: Mapped[str] = mapped_column(String(30), default="E10")

    geocoding_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    nominatim_url: Mapped[str] = mapped_column(
        String(255), default="https://nominatim.openstreetmap.org/search"
    )
    tile_url: Mapped[str] = mapped_column(
        String(255), default="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
    )
    tile_attribution: Mapped[str] = mapped_column(
        String(255), default="&copy; OpenStreetMap contributors"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    brand_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    color: Mapped[str] = mapped_column(String(20), default="#2563eb")
    photo_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tank_capacity_l: Mapped[float | None] = mapped_column(Float, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    entries: Mapped[list["FuelEntry"]] = relationship(
        back_populates="vehicle", cascade="all, delete-orphan",
        order_by="FuelEntry.date, FuelEntry.id",
    )


class Station(Base):
    __tablename__ = "stations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    entries: Mapped[list["FuelEntry"]] = relationship(back_populates="station")


class FuelEntry(Base):
    __tablename__ = "fuel_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    entry_type: Mapped[str] = mapped_column(String(20), default="fuel")  # 'fuel' | 'odometer_only'
    date: Mapped[date] = mapped_column(Date)

    liters: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_per_liter: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    odometer_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    fuel_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    full_tank: Mapped[bool] = mapped_column(Boolean, default=True)

    station_id: Mapped[int | None] = mapped_column(ForeignKey("stations.id"), nullable=True)

    # Fields derived exactly from the other two of liters/price/total
    # (mathematically exact, flagged only for transparency).
    computed_fields: Mapped[list] = mapped_column(JSON, default=list)
    # Fields approximated from the average consumption (a real estimate).
    estimated_fields: Mapped[list] = mapped_column(JSON, default=list)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )

    vehicle: Mapped["Vehicle"] = relationship(back_populates="entries")
    station: Mapped["Station | None"] = relationship(back_populates="entries")
