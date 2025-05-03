import os
import shutil

SOURCE_DIR = os.path.abspath(os.path.dirname(__file__))
DEST_DIR = '/Users/rossfreedman/my_work/rally'

def backup():
    if not os.path.exists(DEST_DIR):
        os.makedirs(DEST_DIR)
    for root, dirs, files in os.walk(SOURCE_DIR):
        rel_root = os.path.relpath(root, SOURCE_DIR)
        dest_root = os.path.join(DEST_DIR, rel_root) if rel_root != '.' else DEST_DIR
        if not os.path.exists(dest_root):
            os.makedirs(dest_root)
        for file in files:
            src_file = os.path.join(root, file)
            rel_file = os.path.relpath(src_file, SOURCE_DIR)
            dest_file = os.path.join(dest_root, file)
            shutil.copy2(src_file, dest_file)
            print(f'Copied: {rel_file}')
    print(f'Backup complete! All files copied to {DEST_DIR}')

if __name__ == '__main__':
    backup() 