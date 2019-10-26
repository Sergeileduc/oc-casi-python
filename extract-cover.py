#!/usr/bin/python3
# -*-coding:utf-8 -*-
"""Extract cover."""

import sys
import os

import zipfile


# Local file is the script argument
local_file = sys.argv[1]


def extract_cover(arc_name):
    """Extract 1st jpg found in archive (zip or cbz)."""
    with zipfile.ZipFile(arc_name, 'r') as zf:
        img_list = zf.namelist()
        jpg_list = [i for i in img_list if (
            i.endswith(".jpg") or i.endswith(".jpeg"))]
        jpg_list.sort()
        cover = jpg_list[0]
        file_data = zf.read(cover)
    with open(os.path.basename(cover), "wb") as fout:
        fout.write(file_data)

    return os.path.basename(cover)


cover = extract_cover(local_file)
