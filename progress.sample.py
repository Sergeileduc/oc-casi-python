#!/usr/bin/python3
# -*-coding:utf-8 -*-

from datetime import datetime
import os
import sys

import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as mb
from tkinter import END, SEL, INSERT

import math
import time

import requests
import requests.exceptions


import owncloud  # pip install pyocclient

user = "username"
password = "password"
server = "http://server"
API_PATH = "ocs/v1.php/apps/files_sharing/api/v1"

cloud_dir = "Edit/"


def get_base_name(local_file):
    # Get file basename
    if os.path.isfile(local_file):
        basename = os.path.basename(local_file)
        print(f"Basename is : {basename}")
        return basename


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
        print(f"before upload : {datetime.now()}")
        if self._put_file_chunked():
            print(f"after upload : {datetime.now()}")
            self.progress.destroy()
            print(f"after destroy : {datetime.now()}")
            print(f"before share : {datetime.now()}")
            # self.withdraw()
            self.share()
            print(f"after share : {datetime.now()}")

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


# OWNCLOUD
# Login

time1 = datetime.now()

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


app = UploadApp(oc=oc, local_file=local_file, remote_path="Edit/")
app.mainloop()

time2 = datetime.now()

print(f"Duration : {time2 - time1}")

print("End of program")
