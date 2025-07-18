from PIL import Image
from pathlib import Path

# Set folder path
input_folder = Path('./data/backdrops')
output_folder = input_folder / 'converted'

# Create output folder if it doesn't exist
output_folder.mkdir(parents=True, exist_ok=True)

# Supported formats
valid_extensions = ['.jpg', '.jpeg', '.png']
resize_size = (1920, 1080)

for input_path in input_folder.iterdir():
    if input_path.suffix.lower() in valid_extensions:
        base_name = input_path.stem
        output_path = output_folder / f"{base_name}.avif"

        try:
            with Image.open(input_path) as img:
                img = img.convert("RGB")
                img = img.resize(resize_size)

                img.save(output_path, format='AVIF', lossless=True)
                print(f"Converted: {input_path.name} → {output_path.name}")
        except Exception as e:
            print(f"Failed to process {input_path.name}: {e}")
