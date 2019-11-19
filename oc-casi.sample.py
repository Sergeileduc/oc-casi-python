#!/usr/bin/python3
# -*-coding:utf-8 -*-
"""Upload file to Onwcloud, extract cover, and upload to casimages.

Return BBcode.
"""

import math
import os
import sys
import time

import tkinter as tk
from tkinter import ttk
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

redim_val = 640

cloud_dir = ""
cover_bool = False
paths = ".owncloud_paths.txt"

# Check command line arguments
if len(sys.argv) < 2:
    print("Missing command line argument (cbz file)")
    sys.exit()


def get_base_name(local_file):
    """Get file basename."""
    if os.path.isfile(local_file):
        basename = os.path.basename(local_file)
        print(f"Basename is : {basename}")
        return basename


def no_ext(basename):
    return os.path.splitext(basename)[0]


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


class OcExplorer(tk.Toplevel):

    def __init__(self, master=None, file_=None):
        tk.Toplevel.__init__(self, master)
        # self.racine = master

        self.folder_path = "/"
        self.previous_folder_path = []
        self.folder_name = ""

        self.folder_list = []

        self.oc = owncloud.Client(server)
        self._login()

        self.frame = tk.Frame(self)
        self.lb = tk.Listbox(self.frame, width=60, height=15,
                             font=("Helvetica", 12))
        self.frame.pack()

        self.scrollbar = tk.Scrollbar(self.frame, orient="vertical")
        self.scrollbar.config(command=self.lb.yview)
        self.scrollbar.pack(side="right", fill="y")

        self.lb.config(yscrollcommand=self.scrollbar.set)
        self.lb.pack(side="left", fill="y")

        self.bottom_bar = tk.Frame(self)
        self.bottom_bar.pack(side='bottom')
        tk.Button(self.bottom_bar, text="Précédent", command=self._up).pack(side=LEFT)  # noqa:E501
        tk.Button(self.bottom_bar, text="Ajouter le chemin", command=self._select).pack(side=LEFT)  # noqa:E501
        # tk.Button(self.bottom_bar, text="Edit", command=self._edit).pack(side=LEFT)  # noqa:E501
        # tk.Button(self.bottom_bar, text="Select", command=self._select).pack(side=LEFT)  # noqa:E501
        # tk.Button(self.bottom_bar, text="Quit", command=self._quit).pack(side=LEFT)  # noqa:E501

        self._populate_list()
        self.lb.bind('<Double-Button-1>', self.double_click)

    def double_click(self, event):
        widget = event.widget
        selection = widget.curselection()
        index = selection[0]
        # value = widget.get(selection[0])
        # print("selection:", selection, ": '%s'" % value)
        self.previous_folder_path.append(self.folder_path)
        self.folder_path = self.folder_list[index]["path"]

        print(self.folder_path)
        self.folder_list = []
        self.lb.delete(0, tk.END)
        # print('double mouse click event')
        self._populate_list()

    def _login(self):
        self.oc.login(user, password)
        print("Logged in !")

    def _up(self):
        self.folder_list = []
        self.lb.delete(0, tk.END)
        self.folder_path = self.previous_folder_path.pop()
        self._populate_list()

    def _select(self):
        try:
            sel = self.lb.curselection()[0]
            s = self.folder_list[sel]["path"]
        except IndexError:
            s = self.folder_path

        # print(f"Cloud dir = {self.cloud_dir}")
        self.master.new_dir = s[1:] if s.startswith("/") else s
        # self.master.destroy()
        self.destroy()

    def _populate_list(self):
        list_dir = self.oc.list(self.folder_path, depth=1)
        for _, file in enumerate(list_dir, 1):
            if file.is_dir():
                name = file.get_name()
                # full_path = file.get_path() + '/' + newName
                full_path = file.get_path()
                self.folder_list.append({'path': full_path, 'name': name})

        [self.lb.insert(END, item["name"]) for item in self.folder_list]


class PathChoice(tk.Tk):

    def __init__(self, *args, file_=None, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)

        self.paths_file = os.path.join(Path.home(), file_)
        self.paths_list = []

        self.selected_cloud_dir = ""
        self.redim = tk.StringVar()
        self.choices = ["640", "320", "125", "Miniature"]

        self.redim.set(self.choices[0])

        self._init_file()
        self._read_file()
        # self._print_list()

        # One frame for lisbox and scrollbar
        self.frame = tk.Frame(self)
        self.lb = tk.Listbox(self.frame, width=60, height=15,
                             font=("Helvetica", 12))
        self.frame.pack()
        [self.lb.insert(END, item) for item in self.paths_list]

        self.scrollbar = tk.Scrollbar(self.frame, orient="vertical")
        self.scrollbar.config(command=self.lb.yview)
        self.scrollbar.pack(side="right", fill="y")

        self.lb.config(yscrollcommand=self.scrollbar.set)
        self.lb.pack(side="left", fill="y")

        # Another Frame for buttons
        self.button_bar = tk.Frame(self)
        self.button_bar.pack()
        tk.Button(self.button_bar, text="Suppimer", command=self._remove).pack(side=LEFT)  # noqa:E501
        tk.Button(self.button_bar, text="Nouveau chemin", command=self._add).pack(side=LEFT)  # noqa:E501
        tk.Button(self.button_bar, text="Sélectionner et uploader", command=self._select).pack(side=LEFT)  # noqa:E501
        tk.Button(self.button_bar, text="Sauver et Quitter", command=self._quit).pack(side=LEFT)  # noqa:E501

        # Another Frame for checkbox
        self.bottom_bar = tk.Frame(self)
        self.check_casi = tk.IntVar()
        self.c = tk.Checkbutton(self.bottom_bar, text="Et uploader la cover sur Casimages\nDonne un lien de partage avec balise [img]",  # noqa:E501
                                variable=self.check_casi)

        self.choice = tk.OptionMenu(self.bottom_bar, self.redim, *self.choices)

        self.bottom_bar.pack(side='bottom')
        self.c.pack(side='left', padx=30)
        self.choice.configure(width=20)
        self.choice.pack(side='right')
        # self.c = tk.Checkbutton(self.bottom_bar, text="Enable Tab",
        #                         variable=self.check_casi,
        #                         command=self.cb)

    def _init_file(self):
        # Create file if not exists
        with open(self.paths_file, 'a'):
            pass

    def _read_file(self):
        # Read file
        with open(self.paths_file, 'r') as f:
            self.paths_list = f.read().splitlines()

    def _print_list(self):
        for p in self.paths_list:
            print(p)

    def _remove(self):
        sel = self.lb.curselection()
        if len(sel) > 0:
            index = self.paths_list.index(self.lb.get(sel[0]))
            self.lb.delete(sel)
            self.paths_list.pop(index)

    def _add(self):
        self.new_dir = ""
        self.wait_window(self._add_path())
        if self.new_dir:
            print(f"Adding : {self.new_dir}")
            self.paths_list.append(self.new_dir)
            self.lb.insert(END, self.new_dir)
        # self.lb.insert(END, self.paths_list[-1])

    def _select(self):
        self._save_file()
        self.selected_cloud_dir = self.lb.get(self.lb.curselection())
        self.destroy()

    def _quit(self):
        self._save_file()
        self.destroy()
        sys.exit()

    def _add_path(self):
        """Create tkinter 'add path' window."""
        # top = tk.Toplevel()
        top = OcExplorer(self)
        return top

    def _save_file(self):
        self.paths_list.sort()
        with open(self.paths_file, 'w') as f:
            f.writelines([(i + "\n") for i in self.paths_list if i])


class UploadApp(tk.Tk):

    def __init__(self, *args,
                 oc=None, local_file=None, remote_path=None,
                 **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        # self.overrideredirect(1)
        # self.wm_attributes('-type', 'splash')

        self.local_file = sys.argv[1]

        self.oc = oc
        self.local_file = local_file
        self.basename = get_base_name(self.local_file)
        self.remote_path = remote_path

        self.progress = ttk.Progressbar(self, orient="horizontal",
                                        length=400, mode="determinate")
        self.progress.pack()

        self.bytes = 0
        self.maxbytes = 0
        self.center()
        self.upload()

    def center(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry('{}x{}+{}+{}'.format(width, height, x, y))

    def upload(self):
        if self._put_file_chunked():
            # self.progress.destroy()
            # print("Progress is destroyed")
            # self.withdraw()
            # self.share()
            print("End of progressbar window")
            self.destroy()

    def share(self):
        cloud_file = os.path.join(cloud_dir, self.basename)
        self.share_link = oc.share_file_with_link(cloud_file).get_link()
        print(self.share_link)
        self.display_share()

    def display_share(self):
        # self.share_text = tk.Text(master, height=1, exportselection=1)
        self.geometry(f"{600}x{50}")
        self.share_text = tk.Text(self, height=1, exportselection=1)
        self.share_text.insert(1.0, f"[url={self.share_link}]{self.basename}[/url]")  # noqa:E501
        self.share_text.tag_add(SEL, "1.0", END)
        self.share_text.mark_set(INSERT, "1.0")
        self.share_text.see(INSERT)
        self.share_text.pack(fill=tk.BOTH, expand=1)
        # self.deiconify()

    # This code comes from pyocclient
    # https://github.com/owncloud/pyocclient
    def _put_file_chunked(self, **kwargs):
        """Uploads a file using chunks.
        :returns: True if the operation succeeded, False otherwise
        :raises: HTTPResponseError in case an HTTP error status was returned
        """
        chunk_size = kwargs.get('chunk_size', 2 * 1024 * 1024)
        result = True
        transfer_id = int(time.time())

        self.remote_path = owncloud.Client._normalize_path(self.remote_path)
        if self.remote_path.endswith('/'):
            self.remote_path += os.path.basename(self.local_file)

        stat_result = os.stat(self.local_file)

        file_handle = open(self.local_file, 'rb', 8192)
        file_handle.seek(0, os.SEEK_END)
        size = file_handle.tell()
        file_handle.seek(0)

        self.progress["value"] = 0
        self.maxbytes = size
        self.progress["maximum"] = size

        headers = {}
        if kwargs.get('keep_mtime', True):
            headers['X-OC-MTIME'] = str(stat_result.st_mtime)

        if size == 0:
            return self.oc._make_dav_request(
                'PUT',
                self.remote_path,
                data='',
                headers=headers
            )

        chunk_count = int(math.ceil(float(size) / float(chunk_size)))

        if chunk_count > 1:
            headers['OC-CHUNKED'] = '1'

        for chunk_index in range(0, int(chunk_count)):
            data = file_handle.read(chunk_size)
            if chunk_count > 1:
                chunk_name = '%s-chunking-%s-%i-%i' % \
                    (self.remote_path, transfer_id, chunk_count,
                     chunk_index)
            else:
                chunk_name = self.remote_path

            self.progress["value"] = chunk_index * chunk_size
            self.update()

            if not self.oc._make_dav_request(
                    'PUT',
                    chunk_name,
                    data=data,
                    headers=headers
            ):
                result = False
                break

        self.progress["value"] = size
        self.update()
        file_handle.close()
        return result


class Casimages():

    # CASIMAGES
    url = "https://www.casimages.com/"
    url_upload = "https://www.casimages.com/upload_ano_multi.php"
    url_casi_share = "https://www.casimages.com/codes_ano_multi.php?img={}"

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

    def __init__(self, cover, size=640):
        self.cover = cover
        self.size = size
        self.redim = size if size in ["640", "320", "125"] else "640"
        print(f"inside value of redim : {self.redim}")
        self.url_redim = f"https://www.casimages.com/ajax/s_ano_resize.php?dim={self.redim}"  # noqa:E501

        self.cover_id = None

        # Session (keep cookies)
        self.session = requests.Session()

        # Init for cookies
        r = self.session.get(Casimages.url)
        print(r.status_code)

        self._set_redim()

    def _set_redim(self):
        # Redim 640
        self.session.get(self.url_redim)

    def upload_cover(self):
        """Upload cover and return id."""
        with open(self.cover, 'rb') as f:
            file_ = {'Filedata': ('cover', f, 'image/jpg')}
            r = self.session.post(Casimages.url_upload,
                                  files=file_, headers=Casimages.headers)

        self.cover_id = r.text  # casimages share page ID
        # delete cover
        os.remove(self.cover)
        return self.cover_id

    def get_share_url(self):
        r = self.session.get(Casimages.url_casi_share.format(self.cover_id))
        soup = BeautifulSoup(r.text, 'html.parser')

        form_rows = soup.select("div.col-sm-9 > div.form-row")
        form_cols = form_rows[2].select("div.form-group.col-lg-6 > input")
        if self.size != "Miniature":
            self.cover_url = form_cols[1]["value"]
        else:
            self.cover_url = form_cols[0]["value"]
        return self.cover_url


class OutputShare(tk.Tk):

    def __init__(self, *args,
                 with_cover=False, name=None, share=None, cover=None,
                 **kwargs):

        tk.Tk.__init__(self, *args, **kwargs)

        self.with_cover = with_cover
        self.name = name
        self.share = share
        self.cover = cover

        self.bbcode = ""
        self._make_share_bbcode()

        # First line
        w1 = tk.Text(self, width=140, height=1, font=("Helvetica", 11),
                     exportselection=1)
        w1.insert(1.0, self.share)
        w1.pack(pady=10, fill=tk.BOTH, expand=1)

        # Second line
        w2 = tk.Text(self, width=140, height=1, font=("Helvetica", 11),
                     exportselection=1)
        w2.insert(1.0, self.bbcode)
        w2.tag_add(SEL, "1.0", END)
        w2.mark_set(INSERT, "1.0")
        w2.see(INSERT)
        w2.pack(pady=10, fill=tk.BOTH, expand=1)

        # Center output
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry('{}x{}+{}+{}'.format(width, height, x, y))

    def _make_share_bbcode(self):
        if self.with_cover:
            self.bbcode = f"[url={self.share}][img]{self.cover}[/img][/url]"
        else:
            new_name = no_ext(self.name)
            self.bbcode = f"[url={self.share}]{new_name}[/url]"


# MAIN PROGRAM here :
app = PathChoice(file_=paths)
app.mainloop()

print("GUI has closed")
cloud_dir = app.selected_cloud_dir
cover_bool = bool(app.check_casi.get())
print(f"Choice for cover upload is : {cover_bool}")

redim_val = app.redim.get()
print(f"Redim val is : {redim_val}")

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
    app = UploadApp(oc=oc, local_file=local_file, remote_path=cloud_dir)
    app.mainloop()
except Exception as e:
    print(e)

# Remote path of the file :
cloud_file = os.path.join(cloud_dir, basename)
# Share the file
share = oc.share_file_with_link(cloud_file).get_link()
# print(share)

if zipfile.is_zipfile(local_file) and cover_bool:
    print("Is zip AND with cover upload")
    cover = extract_cover(local_file)
    print(cover)

    casi_upload = Casimages(cover, size=redim_val)
    casi_upload.upload_cover()
    cover_url = casi_upload.get_share_url()

    print("**********************************************")
    print(share)
    print(cover_url)
    print(f"[url={share}][img]{cover_url}[/img][/url]")
    print("**********************************************")

    output = OutputShare(with_cover=True, share=share, cover=cover_url)
    output.mainloop()

else:
    print("No cover upload (or no zip)")
    print("**********************************************")
    print(share)
    print(f"[url={share}]{no_ext(basename)}[/url]")
    print("**********************************************")
    output = OutputShare(with_cover=False, name=basename, share=share)
    output.mainloop()
