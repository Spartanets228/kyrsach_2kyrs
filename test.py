import os

def get_files_and_sizes(start_path):
    file_info = []
    for root, dirs, files in os.walk(start_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                size = os.path.getsize(file_path)
                file_info.append((file_path, size))
            except OSError as e:
                print(f"Ошибка при доступе к файлу {file_path}: {e}")
    return file_info

start_path = "C:\\"  
files = get_files_and_sizes(start_path)

for file_path, size in files:
    print(f"{file_path}: {size} байт")
