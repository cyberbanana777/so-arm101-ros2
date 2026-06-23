import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'camera_driver'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (
            os.path.join("share", package_name, "launch"),
            glob("launch/*.launch.py"),
        ),
        (
            os.path.join("share", package_name, "config"),
            glob("config/*.yaml"),
        ),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='banana-killer',
    maintainer_email='sashagrachev2005@gmail.com',
    description='Simple camera driver based on python-opencv',
    license='MIT',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'camera_driver = camera_driver.camera_driver:main'
        ],
    },
)
