from setuptools import setup, find_packages
from sys import argv


with open('requirements.txt') as f:
    requirements = f.read().splitlines()

with open("README.rst") as rfile:
    readme = rfile.read()

setup_requirements = []
# prevent pytest-runner from being installed on every invocation
if {'pytest', 'test', 'ptr'}.intersection(argv):
    setup_requirements.append("pytest-runner")


setup(
    name="gsmodutils",
    version="0.0.3",
    description="Utilities for the management and testing of genome scale models in  a cross platform, open manner.",
    long_description=readme,
    long_description_content_type='text/x-rst',
    zip_safe=False,
    author="James Gilbert",
    install_requires=requirements,
    author_email="james.gilbert@nottingham.ac.uk",
    url="",
    license="Apache",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'scrumpy_to_cobra=gsmodutils.utils.scrumpy:scrumpy_to_cobra',
            'gsmodutils=gsmodutils.cli:cli',
        ],
    },
    setup_requires=setup_requirements,
    tests_require=['pytest'],
    include_package_data=True,

    classifiers=[
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Bio-Informatics'
    ],
    platforms="GNU/Linux, Mac OS X >= 10.7, Microsoft Windows >= 7",
)
