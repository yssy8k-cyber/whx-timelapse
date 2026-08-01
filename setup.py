from setuptools import find_packages, setup


setup(
    name="rtsp-timelapse",
    version="0.1.0",
    description="Capture RTSP snapshots and render them into timelapse videos with FFmpeg",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    packages=find_packages("src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
    install_requires=["PyQt6>=6.6"],
    extras_require={"test": ["pytest>=7"]},
    package_data={"timelapse": ["assets/*.jpg"]},
    entry_points={"console_scripts": ["timelapse=timelapse.cli:main"]},
)
