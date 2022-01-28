from pathlib import Path

from setuptools import setup, find_packages

BASE_DIR = Path(__file__).parent.resolve(strict=True)
VERSION = '0.0.1'
PACKAGE_NAME = 'pyzshell'
DATA_FILES_EXTENSIONS = ['*.txt', '*.json', '*.js']
PACKAGES = [p for p in find_packages() if not p.startswith('tests')]


def parse_requirements():
    reqs = []
    with open(BASE_DIR / 'requirements.txt', 'r') as fd:
        for line in fd.readlines():
            line = line.strip()
            if line:
                reqs.append(line)
    return reqs


def get_description():
    return (BASE_DIR / 'README.md').read_text()


def get_data_files():
    data_files = ['requirements.txt']
    package_dir = Path(__file__).parent
    for extension in DATA_FILES_EXTENSIONS:
        for file in (package_dir / PACKAGE_NAME).glob(f'**/{extension}'):
            data_files.append(str(file.relative_to(package_dir)))
    return data_files


if __name__ == '__main__':
    setup(
        version=VERSION,
        name=PACKAGE_NAME,
        description='zShell client',
        long_description=get_description(),
        long_description_content_type='text/markdown',
        cmdclass={},
        packages=PACKAGES,
        include_package_data=True,
        data_files=[('.', get_data_files())],
        author='DoronZ',
        author_email='doron88@gmail.com',
        license='GNU GENERAL PUBLIC LICENSE - Version 3, 29 June 2007',
        install_requires=parse_requirements(),
        entry_points={
            'console_scripts': ['pyzshell=pyzshell.__main__:cli',
                                ],
        },
        classifiers=[
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: 3.8',
            'Programming Language :: Python :: 3.9',
            'Programming Language :: Python :: 3.10',
        ],
        url='https://github.com/doronz88/zshell',
        project_urls={
            'pymobiledevice3': 'https://github.com/doronz88/zshell'
        },
        tests_require=['pytest', 'cmd2_ext_test'],
    )