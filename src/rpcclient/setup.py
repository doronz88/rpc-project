from pathlib import Path

from setuptools import find_packages, setup

BASE_DIR = Path(__file__).parent.resolve(strict=True)
VERSION = '3.15.5'
PACKAGE_NAME = 'rpcclient'
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
    # on Windows, read_text() will replace the emoji unicode characters
    return (BASE_DIR / 'README.md').read_text(errors='ignore')


if __name__ == '__main__':
    setup(
        version=VERSION,
        name=PACKAGE_NAME,
        description='rpcclient for connecting with the rpcserver',
        long_description=get_description(),
        long_description_content_type='text/markdown',
        cmdclass={},
        packages=PACKAGES,
        include_package_data=True,
        author='DoronZ',
        author_email='doron88@gmail.com',
        license='GNU GENERAL PUBLIC LICENSE - Version 3, 29 June 2007',
        install_requires=parse_requirements(),
        entry_points={
            'console_scripts': ['rpcclient=rpcclient.__main__:cli',
                                ],
        },
        classifiers=[
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: 3.8',
            'Programming Language :: Python :: 3.9',
            'Programming Language :: Python :: 3.10',
            'Programming Language :: Python :: 3.11',
        ],
        url='https://github.com/doronz88/rpc-project',
        project_urls={
            'rpc-project': 'https://github.com/doronz88/rpc-project'
        },
        tests_require=['pytest', ],
    )
