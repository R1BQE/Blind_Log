# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.win32.versioninfo import VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct
from PyInstaller.utils.hooks import collect_all

# Собираем всё содержимое пакета transliterate
transliterate_datas, transliterate_binaries, transliterate_hiddenimports = collect_all('transliterate')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=transliterate_binaries,
    datas=[
        ('help.htm', '.'),
        ('help_en.htm', '.'),
        ('locales', 'locales'),
        ('version.txt', '.'),
        ('nvdaControllerClient64.dll', '.'),
        ('changeLog.txt', '.'),
    ] + transliterate_datas,
    hiddenimports=[
        'transliterate',
        'transliterate.base',
        'transliterate.contrib.languages.ru',
        'requests',
        'xml.etree.ElementTree',
    ] + transliterate_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Blind_log',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=eval(open('version.txt', encoding='utf-8').read()),
)
