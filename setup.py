from setuptools import setup

setup(
    name="pychubby",
    version="0.0.1",
    author="Jan Krepl",
    author_email="kjan.official@gmail.com",
    description="Face warping",
    url="https://github.com/jankrepl/pychubby",
    packages=["pychubby"],
    classifiers=[
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "Programming Language :: C",
        "Programming Language :: Python",
        "Topic :: Software Development",
        "Topic :: Scientific/Engineering",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Operating System :: Unix",
        "Operating System :: MacOS",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        ("Programming Language :: Python :: " "Implementation :: CPython"),
    ],
    install_requires=[
        "click>=7.0",
        "dlib",
        "matplotlib>=2.0.0",
        "numpy>=1.16.4",
        "opencv-python>=4.1.0.25",
        "scikit-image",
    ],
    extras_require={
        "dev": ["codecov", "flake8", "pytest>=3.6", "pytest-cov", "tox"],
        "docs": ["sphinx", "sphinx_rtd_theme"],
    },
    entry_points={"console_scripts": ["pc = pychubby.cli:cli"]},
)
