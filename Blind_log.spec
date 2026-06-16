# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.win32.versioninfo import VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct
from PyInstaller.utils.hooks import collect_all

# Собираем всё содержимое пакета transliterate
transliterate_datas, transliterate_binaries, transliterate_hiddenimports = collect_all('transliterate')

# Собираем accessible_output3 со всеми DLL
ao3_datas, ao3_binaries, ao3_hiddenimports = collect_all('accessible_output3')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=transliterate_binaries + ao3_binaries,
    datas=[
        ('help.htm', '.'),
        ('help_en.htm', '.'),
        ('locales', 'locales'),
        ('version.txt', '.'),
        ('changeLog.txt', '.'),
    ] + transliterate_datas + ao3_datas,
    hiddenimports=[
        'transliterate',
        'transliterate.base',
        'transliterate.contrib.languages.ru',
        'requests',
        'xml.etree.ElementTree',
        'accessible_output3',
        'accessible_output3.outputs.auto',
        'accessible_output3.outputs.nvda',
        'accessible_output3.outputs.jaws',
        'accessible_output3.outputs.sapi5',
    ] + transliterate_hiddenimports + ao3_hiddenimports,
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
