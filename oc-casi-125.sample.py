#!/usr/bin/python3
# -*-coding:utf-8 -*-
"""Upload file to Onwcloud, extract cover, and upload to casimages.

Return BBcode.
"""

import sys
import os
# from tkinter import *
import tkinter as tk
import tkinter.messagebox as mb
from tkinter import END, LEFT, SEL, INSERT

import zipfile
from pathlib import Path
import requests
import requests.exceptions

from bs4 import BeautifulSoup
import owncloud  # pip install pyocclient

user = "username"
password = "password"
server = "http://server"
API_PATH = "ocs/v1.php/apps/files_sharing/api/v1"

redim_val = 125

# Path selection window
# Modify at your will
path_box_width = 500
path_box_height = 250

# Other sizes
size_x = 500
size_y = 250

# Modify this to change final BBCode window size
bbcode_width = 600
bbcode_height = 50

paths_file = os.path.join(Path.home(), ".owncloud_paths.txt")
# print(paths_file)

# Check command line arguments
if len(sys.argv) < 2:
    print("Missing command line argument (cbz file)")
    sys.exit()


# Create file if not exists
with open(paths_file, 'a') as f:
    pass

# Read file
with open(paths_file, 'r') as f:
    paths_list = f.read().splitlines()


cloud_dir = ""


def edit_path(index):
    """Create tkinter 'edit path' window."""
    def edit():
        paths_list[index] = e1.get()
        # print(paths_list)
        top.destroy()

    top = tk.Toplevel()
    pos_x = int(top.winfo_screenwidth() / 2 - size_x / 2)
    pos_y = int(top.winfo_screenheight() / 2 - size_y / 2)
    top.wm_geometry(f"400x50+{pos_x}+{pos_y}")
    e1 = tk.Entry(top, width=50)
    e1.insert(0, paths_list[index])
    e1.pack(fill='x', expand=1)
    tk.Button(top, text="Submit", command=edit).pack()

    # Return reference to toplevel so that
    # root can wait for it to run its course
    return top


def add_path():
    """Create tkinter 'add path' window."""
    def edit():
        paths_list.append(e1.get())
        # print(paths_list)
        top.destroy()

    top = tk.Toplevel()
    pos_x = int(top.winfo_screenwidth() / 2 - size_x / 2)
    pos_y = int(top.winfo_screenheight() / 2 - size_y / 2)
    top.wm_geometry(f"400x50+{pos_x}+{pos_y}")
    e1 = tk.Entry(top, width=50)
    e1.pack(fill='x', expand=1)
    tk.Button(top, text="Submit", command=edit).pack()

    # Return reference to toplevel so that
    # root can wait for it to run its course
    return top


def _edit():
    global lb, paths_list, root
    # Get dictionary from listbox
    sel = lb.curselection()
    if len(sel) > 0:
        indexToEdit = paths_list.index(lb.get(sel[0]))
        lb.delete(sel)
        root.wait_window(edit_path(indexToEdit))
        # print(paths_list[indexToEdit])
        lb.insert(sel, paths_list[indexToEdit])


def _remove():
    sel = lb.curselection()
    if len(sel) > 0:
        index = paths_list.index(lb.get(sel[0]))
        lb.delete(sel)
        paths_list.pop(index)


def _add():
    global lb, root
    root.wait_window(add_path())
    lb.insert(END, paths_list[-1])


def _select():
    global root, cloud_dir
    # sel = lb.curselection()
    cloud_dir = lb.get(lb.curselection())
    root.destroy()


root = tk.Tk()

pos_x = int(root.winfo_screenwidth() / 2 - path_box_width / 2)
pos_y = int(root.winfo_screenheight() / 2 - path_box_height / 2)
root.wm_geometry(f"{path_box_width}x{path_box_height}+{pos_x}+{pos_y}")
lb = tk.Listbox(root)
lb.pack(fill="both")
lb.pack_propagate(True)
[lb.insert(END, item) for item in paths_list]

bottom_bar = tk.Frame(root)
bottom_bar.pack(side='bottom')
tk.Button(bottom_bar, text="Remove", command=_remove).pack(side=LEFT)
tk.Button(bottom_bar, text="Add", command=_add).pack(side=LEFT)
tk.Button(bottom_bar, text="Edit", command=_edit).pack(side=LEFT)
tk.Button(bottom_bar, text="Select", command=_select).pack(side=LEFT)
root.mainloop()

for i in paths_list:
    print(i)

# Saving
paths_list.sort()
with open(paths_file, 'w') as f:
    f.writelines([(i + "\n") for i in paths_list if i])

# Checkint if not empty
if cloud_dir:
    print("********************")
    print(cloud_dir)
else:
    print("Dossier vide non valide")
    mb.askokcancel("Erreur", "Dossier vide (racine) non accepté.")
    sys.exit(1)


# OWNCLOUD
# Login
try:
    oc = owncloud.Client(server)
    oc.login(user, password)
    print("Logged in !")
except requests.exceptions.MissingSchema:
    print("Erreur.")
    print(f"Veuillez configurer avec une url correcte")
    mb.askokcancel("Erreur", "URL incorrecte.")
    sys.exit(1)
except owncloud.owncloud.HTTPResponseError:
    print("Erreur.")
    print(" Veuillez configurer "
          "avec utilisateur et mot de passe valide")
    mb.askokcancel("Erreur", "Login/password ou server incorrects.")
    # print(e)
    sys.exit(1)

# Check if cloud dir exists :
try:
    list_dir = oc.list(cloud_dir)
    print("YATA !!")
except owncloud.owncloud.HTTPResponseError:
    print("Dossier non valide")
    mb.askokcancel("Erreur", "Dossier invalide")
    oc.logout()
    sys.exit(1)

# Add a trailing /
# Documents/Tests --> Documents/Tests/
# cloud_dir = os.path.join(cloud_dir, "")
if cloud_dir[-1] != "/":
    cloud_dir = cloud_dir + "/"
print(cloud_dir)

# Local file is the script argument
local_file = sys.argv[1]

# Get file basename
if os.path.isfile(local_file):
    basename = os.path.basename(local_file)
    print(basename)

try:
    oc.put_file(cloud_dir, local_file)
    print("Done")
except Exception as e:
    print(e)

# Remote path of the file :
cloud_file = os.path.join(cloud_dir, basename)

# Share the file
share = oc.share_file_with_link(cloud_file).get_link()
print(share)

# ZIP ?
if zipfile.is_zipfile(local_file):
    print("ZIIIIP")
else:
    print("NOOO ZIIIIP")
    # TODO
    # Print share link, without cover


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
url_redim = f"https://www.casimages.com/ajax/s_ano_resize.php?dim={redim_val}"
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
print(share)
print(cover_url)

print(f"[url={share}][img]{cover_url}[/img][/url]")


# GUI output
master = tk.Tk()
pos_x = int(master.winfo_screenwidth() / 2 - size_x / 2)
pos_y = int(master.winfo_screenheight() / 2 - size_y / 2)
master.wm_geometry(f"{bbcode_width}x{bbcode_height}+{pos_x}+{pos_y}")
w = tk.Text(master, height=1, exportselection=1)
w.insert(1.0, f"[url={share}][img]{cover_url}[/img][/url]")
w.tag_add(SEL, "1.0", END)
w.mark_set(INSERT, "1.0")
w.see(INSERT)
w.pack(fill=tk.BOTH, expand=1)
master.mainloop()
