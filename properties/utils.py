from PIL import Image, ImageOps
import os
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from io import BytesIO


def compress_image(image_file, max_width=1200, max_height=800, quality=85):
    """
    Compress and optimize an image file.

    Args:
        image_file: Django File object
        max_width: Maximum width in pixels
        max_height: Maximum height in pixels
        quality: JPEG quality (1-100)

    Returns:
        ContentFile: Optimized image as ContentFile
    """
    try:
        # Open image with PIL
        image = Image.open(image_file)

        # Convert to RGB if necessary (for PNG with transparency)
        if image.mode in ('RGBA', 'LA', 'P'):
            # Create white background
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')

        # Get original dimensions
        width, height = image.size

        # Calculate new dimensions maintaining aspect ratio
        if width > max_width or height > max_height:
            ratio = min(max_width / width, max_height / height)
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Auto-rotate based on EXIF data
        image = ImageOps.exif_transpose(image)

        # Save to BytesIO with optimization
        output = BytesIO()
        image.save(output, format='JPEG', quality=quality, optimize=True, progressive=True)
        output.seek(0)

        # Create ContentFile
        filename = os.path.splitext(image_file.name)[0] + '.jpg'
        content_file = ContentFile(output.getvalue(), name=filename)

        # Close images to free memory
        image.close()
        output.close()

        return content_file

    except Exception as e:
        # If compression fails, return original file
        print(f"Image compression failed: {e}")
        return image_file


def create_thumbnail(image_file, size=(300, 300)):
    """
    Create a thumbnail from an image file.

    Args:
        image_file: Django File object
        size: Tuple of (width, height) for thumbnail

    Returns:
        ContentFile: Thumbnail as ContentFile
    """
    try:
        # Open image with PIL
        image = Image.open(image_file)

        # Convert to RGB if necessary
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')

        # Auto-rotate based on EXIF data
        image = ImageOps.exif_transpose(image)

        # Create thumbnail
        image.thumbnail(size, Image.Resampling.LANCZOS)

        # Save to BytesIO
        output = BytesIO()
        image.save(output, format='JPEG', quality=80, optimize=True)
        output.seek(0)

        # Create ContentFile
        filename = os.path.splitext(image_file.name)[0] + '_thumb.jpg'
        content_file = ContentFile(output.getvalue(), name=filename)

        # Close images to free memory
        image.close()
        output.close()

        return content_file

    except Exception as e:
        # If thumbnail creation fails, return None
        print(f"Thumbnail creation failed: {e}")
        return None


def optimize_image_upload(image_file, field_name='image'):
    """
    Optimize an uploaded image for web use.

    Args:
        image_file: Uploaded file from request.FILES
        field_name: Name of the field for naming purposes

    Returns:
        dict: Dictionary with 'original', 'compressed', and 'thumbnail' keys
    """
    result = {
        'original': image_file,
        'compressed': None,
        'thumbnail': None
    }

    try:
        # Compress main image
        compressed = compress_image(image_file)
        if compressed != image_file:  # Only if compression actually happened
            result['compressed'] = compressed

        # Create thumbnail
        thumbnail = create_thumbnail(image_file)
        if thumbnail:
            result['thumbnail'] = thumbnail

    except Exception as e:
        print(f"Image optimization failed: {e}")
        # Return original if optimization fails
        pass

    return result