import os
import sys
import platform
from typing import List, Tuple
from cx_Freeze import setup, Executable

# https://github.com/marcelotduarte/cx_Freeze/issues/1288
base = None

proj_root = os.path.abspath(os.path.dirname(__file__))


include_files: List[Tuple[str, str]] = [
    (f'{proj_root}/config.yml', 'config.yml'),
    (f'{proj_root}/data', 'data'),
    (f'{proj_root}/image', 'image')
]

includes = []

for file in os.listdir('javsp/web'):
    name, ext = os.path.splitext(file)
    if ext == '.py':
        includes.append('javsp.web.' + name)

packages = [ 
    'pendulum' # pydantic_extra_types depends on pendulum
]

# 平台特定的构建配置
if platform.system() == 'Darwin':  # macOS
    build_exe = {
        'include_files': include_files,
        'includes': includes,
        'excludes': ['unittest', 'test'],
        'packages': packages,
        'zip_include_packages': ['*'],
        'zip_exclude_packages': [],
        'include_msvcr': True,
        'silent': True,
    }
elif platform.system() == 'Windows':
    build_exe = {
        'include_files': include_files,
        'includes': includes,
        'excludes': ['unittest'],
        'packages': packages,
        'include_msvcr': True,
    }
else:  # Linux
    build_exe = {
        'include_files': include_files,
        'includes': includes,
        'excludes': ['unittest'],
        'packages': packages,
    }

# 根据平台选择可执行文件配置
if platform.system() == 'Darwin':  # macOS
    # macOS 命令行可执行文件
    javsp = Executable(
        './javsp/__main__.py',
        target_name='javsp',  # 使用小写以符合命令行惯例
        base=None,  # 不使用控制台基础，保持为普通命令行程序
        icon=None,  # macOS 不使用 .ico 格式
    )
elif platform.system() == 'Windows':
    # Windows 可执行文件
    javsp = Executable(
        './javsp/__main__.py',
        target_name='JavSP',
        base=None,
        icon='./image/JavSP.ico',
    )
else:  # Linux
    # Linux 可执行文件
    javsp = Executable(
        './javsp/__main__.py',
        target_name='javsp',
        base=None,
        icon=None,
    )

setup(
    name='JavSP',
    options = {'build_exe': build_exe}, 
    executables=[javsp]
)

