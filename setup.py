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
    'pendulum',  # pydantic_extra_types depends on pendulum
    'requests',
    'colorama',
    'pathlib',
    'json',
    'hashlib',
    'logging',
    'threading',
    'concurrent.futures',
    'urllib.parse',
    'argparse',
    'datetime',
    're',
    'shutil',
    'os',
    'sys',
    'time',
    'itertools'
]

# 平台特定的构建配置
if platform.system() == 'Darwin':  # macOS
    build_exe = {
        'include_files': include_files,
        'includes': includes,
        'excludes': ['unittest', 'test', 'pytest', 'tkinter.test'],
        'packages': packages,
        'zip_include_packages': ['*'],
        'zip_exclude_packages': [],
        'include_msvcr': True,
        'silent': True,
        'optimize': 2,
        'zip_include_packages': ['*'],
        'replace_paths': [('*', 'javsp')],
    }
elif platform.system() == 'Windows':
    build_exe = {
        'include_files': include_files,
        'includes': includes,
        'excludes': ['unittest', 'test', 'pytest'],
        'packages': packages,
        'include_msvcr': True,
        'optimize': 2,
    }
else:  # Linux
    build_exe = {
        'include_files': include_files,
        'includes': includes,
        'excludes': ['unittest', 'test', 'pytest'],
        'packages': packages,
        'optimize': 2,
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
    version='2.8.0',
    description='汇总多站点数据的AV元数据刮削器',
    author='Yuukiy',
    author_email='yuukisil@outlook.com',
    url='https://github.com/Yuukiy/JavSP',
    license='GPL-3.0',
    options={'build_exe': build_exe},
    executables=[javsp],
    python_requires='>=3.8',
    install_requires=[
        'pydantic>=2.0.0',
        'confz>=2.0.0',
        'requests>=2.28.0',
        'colorama>=0.4.0',
        'tqdm>=4.64.0',
        'Pillow>=9.0.0',
        'pydantic-extra-types>=2.0.0',
        'pendulum>=2.1.0',
        'cloudscraper>=1.2.0',
        'cx-Logging>=3.0.0',
        'lxml>=4.9.0',
        'beautifulsoup4>=4.11.0',
        'pretty_errors>=1.2.0',
    ],
    entry_points={
        'console_scripts': [
            'javsp=javsp.__main__:entry',
        ],
    },
)

