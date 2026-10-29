import re
import sys

VERSION_FILE = "version.txt"


def _parse_version_arg(arg):
    """Разбирает аргумент вида 4.12.1 в список [4, 12, 1]."""
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", arg):
        raise ValueError(f"Expected version in X.Y.Z format, got: {arg!r}")
    return [int(part) for part in arg.split(".")]


def _read_current(content):
    m = re.search(r"filevers=\(([\d,\s]+)\)", content)
    if m:
        return [int(p.strip()) for p in m.group(1).split(",")]
    m = re.search(r"StringStruct\('FileVersion', '([\d\.]+)'\)", content)
    if m:
        return [int(p) for p in m.group(1).split(".")]
    raise ValueError("Could not find current version in file.")


def apply_version(content, version):
    """Переписывает в VSVersionInfo только номера версии.

    FileVersion/ProductVersion пишутся в формате X.Y.Z (совпадает с git-тегами),
    filevers/prodvers — в четырёхчастном (X, Y, Z, 0). Все остальные поля
    (описание, автор и т.д.) не затрагиваются.
    """
    major, minor, patch = version
    filevers = f"filevers=({major}, {minor}, {patch}, 0)"
    prodvers = f"prodvers=({major}, {minor}, {patch}, 0)"
    file_version = f"StringStruct('FileVersion', '{major}.{minor}.{patch}')"
    product_version = f"StringStruct('ProductVersion', '{major}.{minor}.{patch}')"
    content = re.sub(r"filevers=\(.*?\)", filevers, content)
    content = re.sub(r"prodvers=\(.*?\)", prodvers, content)
    content = re.sub(r"StringStruct\('FileVersion', '.*?'\)", file_version, content)
    content = re.sub(r"StringStruct\('ProductVersion', '.*?'\)", product_version, content)
    return content


def main(argv=None):
    args = list(sys.argv[1:]) if argv is None else argv

    with open(VERSION_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    if args:
        version = _parse_version_arg(args[0])
    else:
        current = _read_current(content)
        version = [current[0], current[1] + 1, 0]

    content = apply_version(content, version)
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Version updated to {version[0]}.{version[1]}.{version[2]}")


if __name__ == "__main__":
    main()
