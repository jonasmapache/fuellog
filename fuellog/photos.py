"""Vehicle photo upload handling."""
import os

from fastapi import UploadFile

from .config import MAX_PHOTO_BYTES, PHOTOS_DIR
from .models import Vehicle

ALLOWED_PHOTO_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


async def save_vehicle_photo(vehicle: Vehicle, photo: UploadFile | None) -> None:
    if not photo or not photo.filename:
        return
    ext = ALLOWED_PHOTO_TYPES.get(photo.content_type)
    if not ext:
        return  # unknown/disallowed type: ignore silently rather than error
    data = await photo.read()
    if not data or len(data) > MAX_PHOTO_BYTES:
        return
    # remove the previous file if the extension changes
    if vehicle.photo_filename:
        old_path = os.path.join(PHOTOS_DIR, vehicle.photo_filename)
        if os.path.exists(old_path):
            os.remove(old_path)
    dest_name = f"vehicle-{vehicle.id}{ext}"
    with open(os.path.join(PHOTOS_DIR, dest_name), "wb") as f:
        f.write(data)
    vehicle.photo_filename = dest_name


def delete_vehicle_photo(vehicle: Vehicle) -> None:
    if not vehicle.photo_filename:
        return
    path = os.path.join(PHOTOS_DIR, vehicle.photo_filename)
    if os.path.exists(path):
        os.remove(path)
