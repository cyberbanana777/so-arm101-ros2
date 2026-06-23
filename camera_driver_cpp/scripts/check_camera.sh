#!/bin/bash

sudo apt install v4l-utils

v4l2-ctl --list-devices

v4l2-ctl --device=/dev/video0 --list-formats-ext