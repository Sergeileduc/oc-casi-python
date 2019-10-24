#!/usr/bin/python3
# -*-coding:utf-8 -*-
"""Upload file to Onwcloud, extract cover, and upload to casimages.

Return BBcode.
"""

import sys
import os

import tkinter as tk
from tkinter import END, SEL, INSERT

import zipfile
import requests
import requests.exceptions

from bs4 import BeautifulSoup

# Local file is the script argument
local_file = sys.argv[1]

# ZIP ?
if zipfile.is_zipfile(local_file):
    print("ZIIIIP")
else:
    # Display OC share, and exit
    print("NOOO ZIIIIP")


# EXTRACT COVER
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
print(cover)

# CASIMAGES
url = "https://www.casimages.com/"
url_redim = "https://www.casimages.com/ajax/s_ano_resize.php?dim=640"
url_upload = "https://www.casimages.com/upload_ano_multi.php"
url_casi_share = "https://www.casimages.com/codes_ano_multi.php?img={}"

# Session (keep cookies)
session = requests.Session()

# Init for cookies
r = session.get(url)
print(r.status_code)

# Redim 640
r = session.get(url_redim)

headers = {
    "Accept": "application/json",
    "Accept-Language": "fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3",
    "Accept-Encoding": "gzip, deflate, br",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:69.0) Gecko/20100101 Firefox/69.0",  # noqa: E501
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Pragma": "no-cache",
    "X-Requested-With": "XMLHttpRequest"
    }

# Upload
with open(cover, 'rb') as f:
    file_ = {'Filedata': ('cover', f, 'image/jpg')}
    r = session.post(url_upload, files=file_, headers=headers)

cover_id = r.text  # casimages share page ID

# delete cover
os.remove(cover)

# Get image share url
r = session.get(url_casi_share.format(cover_id))
soup = BeautifulSoup(r.text, 'html.parser')

form_rows = soup.select("div.col-sm-9 > div.form-row")
form_cols = form_rows[2].select("div.form-group.col-lg-6 > input")
cover_url = form_cols[1]["value"]

print("**********************************************")
print(cover_url)

print(f"[img]{cover_url}[/img]")


# GUI output
master = tk.Tk()
pos_x = int(master.winfo_screenwidth() / 2 - 600)
pos_y = int(master.winfo_screenheight() / 2)
master.wm_geometry(f"1200x50+{pos_x}+{pos_y}")
w = tk.Text(master, height=1, exportselection=1)
w.insert(1.0, f"[img]{cover_url}[/img]")
w.tag_add(SEL, "1.0", END)
w.mark_set(INSERT, "1.0")
w.see(INSERT)
w.pack(fill=tk.BOTH, expand=1)
master.mainloop()
