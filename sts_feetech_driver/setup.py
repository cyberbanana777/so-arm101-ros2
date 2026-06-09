from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'sts_feetech_driver'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', f'{package_name}', 'config'), glob('config/*.yaml')),
        (os.path.join('share', f'{package_name}', 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='banana-killer',
    maintainer_email='sashagrachev2005@gmail.com',
    description='Action-server for control so arm101 with sts feetech servos',
    license='MIT',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'sts_feetech_driver = sts_feetech_driver.sts_feetech_driver:main'
        ],
    },
)
