"""
Upload media files to Cloudflare R2
"""
import boto3
import os
from pathlib import Path

# Configure R2 client
s3 = boto3.client(
    's3',
    endpoint_url='https://974dd2fd587f660b7a5b75ca1057b741.r2.cloudflarestorage.com',
    aws_access_key_id='372ab68aa19d873e85d0bb25670a6c51',
    aws_secret_access_key='998c84dbce7a5ca9bcdcd9e1fec8d108b3f3d04a55bb2922abbe00fd7fad2d32'
)

BUCKET_NAME = 'reserve-with-ease-media'

def upload_folder(folder_path, prefix=''):
    """Upload all files in a folder to R2"""
    if not os.path.exists(folder_path):
        print(f'[!] Folder not found: {folder_path}')
        return 0
    
    files_uploaded = 0
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            local_path = os.path.join(root, file)
            # Create R2 key (preserve folder structure)
            key = prefix + os.path.relpath(local_path, folder_path)
            
            try:
                s3.upload_file(local_path, BUCKET_NAME, key)
                print(f'[OK] {key}')
                files_uploaded += 1
            except Exception as e:
                print(f'[FAIL] {key} - {e}')
    
    return files_uploaded

print('=' * 50)
print('Uploading media files to Cloudflare R2')
print('=' * 50)

# Get current directory and build paths
BASE_DIR = Path(__file__).resolve().parent
MEDIA_DIR = BASE_DIR / 'media'

print(f'Base dir: {BASE_DIR}')
print(f'Media dir exists: {MEDIA_DIR.exists()}')
print(f'Media dir: {MEDIA_DIR}')
print(f'Contents: {list(MEDIA_DIR.iterdir()) if MEDIA_DIR.exists() else "N/A"}')

# Upload each subfolder
print('\n[*] Uploading payment_receipts...')
count1 = upload_folder(str(MEDIA_DIR / 'payment_receipts'), 'payment_receipts/')

print('\n[*] Uploading profile_pics...')
count2 = upload_folder(str(MEDIA_DIR / 'profile_pics'), 'profile_pics/')

print('\n[*] Uploading property_images...')
count3 = upload_folder(str(MEDIA_DIR / 'property_images'), 'property_images/')

total = (count1 or 0) + (count2 or 0) + (count3 or 0)
print('\n' + '=' * 50)
print(f'[DONE] Upload complete! Total files: {total}')
print('=' * 50)
