import cv2
from deepface import DeepFace
import datetime
from dateutil.relativedelta import relativedelta
import PIL.Image
import PIL.ExifTags
import logging
import piexif
import click
import os

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def estimate_age(image_path: str) -> datetime:
    img = cv2.imread(image_path)
    results  = DeepFace.analyze(img, actions=('age'))
    age  = results[0]['age']
    logger.info(f"estimated age is {age}")
    return age

def estimate_date_of_photo(age, date_of_birth: datetime) -> datetime:
    estimated_date_of_photo =  date_of_birth+relativedelta(years=age)
    logger.info(f'Probable year of photo is { estimated_date_of_photo}')
    return estimated_date_of_photo

def get_exif_date(image_path: str) -> datetime:
    img = PIL.Image.open(image_path)
    exif = {
        PIL.ExifTags.TAGS[k]: v
        for k, v in img._getexif().items()
        if k in PIL.ExifTags.TAGS
    }
    date_time_original_str = exif['DateTimeOriginal']
    logger.info(date_time_original_str)
    date_time_original = datetime.datetime.strptime(date_time_original_str, '%Y:%m:%d %H:%M:%S')
    return date_time_original

def update_exif_date(image_path: str, estimated_date: datetime):
    try:
        # Convert the date to EXIF format (e.g., "2023:10:24 12:00:00")
        exif_date = estimated_date.strftime('%Y:%m:%d %H:%M:%S')

        # Get existing EXIF data to update
        exif_dict = piexif.load(image_path)
        exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = exif_date

        # Save the modified EXIF data back to the image
        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, image_path)

        logger.info(f"Updated EXIF date for {image_path} to {exif_date}")

    except Exception as e:
        logger.error(f"Error updating EXIF date for {image_path}: {e}")


def process_images_in_folder(folder_path, year_of_birth_date):
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            img_path = os.path.join(folder_path, filename)
            process_image(img_path, year_of_birth_date)

def process_image(img_path, year_of_birth_date):
    estimated_age = estimate_age(img_path)
    estimated_date = estimate_date_of_photo(estimated_age, year_of_birth_date)
    exif_date = get_exif_date(img_path)

    if abs((estimated_date - exif_date).days) > 3650:  # 3650 days is approximately 10 years
        click.confirm(f'The estimated date of the photo {os.path.basename(img_path)} differs significantly from the EXIF date. Do you want to update the EXIF date?', abort=True)
        update_exif_date(img_path, estimated_date)
        add_metadata(img_path, year_of_birth_date, estimated_date)

def add_metadata(img_path, year_of_birth_date, estimated_date):
    try:
        exif_dict = piexif.load(img_path)
        metadata_comment = f"born on {year_of_birth_date.strftime('%Y-%m-%d')} and is {estimated_date.year - year_of_birth_date.year} years old."
        exif_dict['0th'][piexif.ImageIFD.ImageDescription] = metadata_comment

        # Save the modified EXIF data back to the image
        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, img_path)

        logger.info(f"Added metadata to {img_path}: {metadata_comment}")

    except Exception as e:
        logger.error(f"Error adding metadata to {img_path}: {e}")

@click.command()
@click.option('--folder_path', default='images/', prompt='Folder path', help='The path to the folder containing image files.')
@click.option('--year_of_birth', prompt='Year of birth', type=int, help='The year of birth.')
def main(folder_path, year_of_birth):
    year_of_birth_date = datetime.datetime(year_of_birth, 1, 1)
    process_images_in_folder(folder_path, year_of_birth_date)

if __name__ == "__main__":
    main()
