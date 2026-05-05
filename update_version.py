import re

version_file = "version.txt"

# Чтение содержимого файла
with open(version_file, "r", encoding="utf-8") as file:
    content = file.read()

# Поиск текущей версии в любом формате (с точками или запятыми)
version_match = re.search(r"filevers=\(([\d,\s]+)\)|StringStruct\('FileVersion', '([\d\.]+)'\)", content)
if not version_match:
    raise ValueError("Could not find current version in file.")

# Получаем версию
if version_match.group(1):
    version_parts = [int(part.strip()) for part in version_match.group(1).split(',')]
else:
    version_parts = [int(part) for part in version_match.group(2).split('.')]

# Увеличиваем минорную версию, сбрасываем patch и build
major, minor = version_parts[0], version_parts[1]
new_version = (major, minor + 1, 0, 0)

# Форматы для замены
new_filevers = f"filevers=({', '.join(map(str, new_version))})"
new_prodvers = f"prodvers=({', '.join(map(str, new_version))})"
new_fileversion = f"StringStruct('FileVersion', '{new_version[0]}.{new_version[1]}.{new_version[2]}.{new_version[3]}')"
new_productversion = f"StringStruct('ProductVersion', '{new_version[0]}.{new_version[1]}.{new_version[2]}.{new_version[3]}')"

# Замены
content = re.sub(r"filevers=\(.*?\)", new_filevers, content)
content = re.sub(r"prodvers=\(.*?\)", new_prodvers, content)
content = re.sub(r"StringStruct\('FileVersion', '.*?'\)", new_fileversion, content)
content = re.sub(r"StringStruct\('ProductVersion', '.*?'\)", new_productversion, content)

# Запись обратно
with open(version_file, "w", encoding="utf-8") as file:
    file.write(content)

print(f"Version updated to {new_version[0]}.{new_version[1]}.{new_version[2]}.{new_version[3]}")
