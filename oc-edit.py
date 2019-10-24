#!/usr/bin/python3
# -*-coding:utf-8 -*-
"""Upload file to folder Edit in Onwcloud.

Return BBcode for public share link.
"""

import sys
import os
import time
from configparser import NoOptionError, NoSectionError
from configparser import ConfigParser
# from tkinter import *
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as mb
from tkinter import END, SEL, INSERT

import requests
import requests.exceptions

import owncloud  # pip install pyocclient
from owncloud import HTTPResponseError
from six.moves.urllib import parse
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor

API_PATH = "ocs/v1.php/apps/files_sharing/api/v1"

CONF = "owncloud.ini"

# Check command line arguments
if len(sys.argv) < 2:
    print("Missing command line argument (cbz file)")
    sys.exit(1)

cloud_dir = "Edit"


# OWNCLOUD
def create_callback(encoder, gui):
    """ Create callback for upload method."""
    encoder_len = encoder.len
    print(encoder_len)

    def callback(monitor):
        # bar.show(monitor.bytes_read)
        percent = int(monitor.bytes_read / encoder_len * 100.0)
        # print(percent)
        gui.percent.set(percent)
        # gui.update_idletasks()
        gui.progress.update()

    return callback


def create_upload(file_, remote_path):
    """Create upload object (with MultipartEncoder).

    Args:
        file_ (str): path of local file
        remote_path (str): remote folder path

    Returns:
        (file, str, MultipartEncoder): file object, remote path,
                                       MultipartEncoder object

    """
    basename = os.path.basename(file_)

    # Verify that path ends with '/'
    if remote_path[-1] == '/':
        remote_path += basename
    else:
        remote_path += '/' + basename

    f = open(file_, 'rb', 8192)
    upload = MultipartEncoder({
        'file': (basename, f)
        })
    return f, remote_path, upload


# All of this is for progress bar...
# Upload is made in the run function
class Uploadbar(tk.Tk):
    """GUI made with tk.TK."""

    title_string = "Progression"
    barwidth = 600

    def __init__(self, local_file, remote_path, occlient):
        """Init Tkinter program with GUI."""
        super().__init__()
        self.title("Progression")
        self.local_file = local_file
        self.remote_path = remote_path
        self.occlient = occlient
        pos_x = int(self.winfo_screenwidth() / 2 - self.barwidth / 2)
        pos_y = int(self.winfo_screenheight() / 2)
        self.geometry(f"+{pos_x}+{pos_y}")
        frame = ttk.Frame(self, width=self.barwidth)
        canvas = tk.Canvas(self)
        self.percent = tk.IntVar()
        self.percent.set(0)
        self.progress = ttk.Progressbar(canvas, orient="horizontal",
                                        variable=self.percent,
                                        mode="determinate")
        frame.pack(fill='x', expand=True)
        canvas.pack(fill='x', expand=True)
        self.progress.pack(fill=tk.BOTH, expand=True)

        self.run()

    def run(self):
        """Search comic on getcomics.info."""
        f, path, upload = create_upload(self.local_file, self.remote_path)

        path = self.occlient._normalize_path(path)

        callback = create_callback(upload, self)
        monitor = MultipartEncoderMonitor(upload, callback)
        start_time = time.time()

        res = self.occlient._session.request(
            'PUT',
            webdav_url + parse.quote(self.occlient._encode_string(path)),
            data=monitor,
            headers={'Content-Type': monitor.content_type}
        )

        print("--- %s seconds ---" % (time.time() - start_time))
        f.close()
        print('\nUpload finished! (Returned status {0} {1})'.format(
            res.status_code, res.reason
            ))
        self.destroy()

        if self.occlient._debug:
            print('DAV status: %i' % res.status_code)
        if res.status_code in [200, 207]:
            return self.occlient._parse_dav_response(res)
        if res.status_code in [204, 201]:
            return True
        raise HTTPResponseError(res)


# Read .ini file
config = ConfigParser()
config.read(CONF)  # read owncloud.ini

# Should work with .get() methods in Python 3.8
# server = config.get('owncloud', 'host')
# user = config.get('owncloud', 'username ')
# password = config.get('owncloud', 'password ')

try:
    server = config['owncloud']['host']
    user = config['owncloud']['username']
    password = config['owncloud']['password']
except (NoOptionError, NoSectionError) as e:
    print(e)
    sys.exit(1)

# webdav url
if not server.endswith('/'):
    webdav_url = server + '/remote.php/dav/files/' + parse.quote(user)
else:
    webdav_url = server + 'remote.php/dav/files/' + parse.quote(user)

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
except owncloud.owncloud.HTTPResponseError as e:
    print("Erreur.")
    print(" Veuillez configurer "
          "avec utilisateur et mot de passe valide")
    mb.askokcancel("Erreur", "Login/password ou server incorrects.")
    print(e)
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
else:
    print("Not a file ! Exit")
    sys.exit(1)

try:
    # oc.put_file(cloud_dir, local_file)
    app = Uploadbar(local_file, cloud_dir, oc)
    app.mainloop()
    print("Done")
except Exception as e:
    print(e)

# Remote path of the file :
cloud_file = os.path.join(cloud_dir, basename)

# Share the file
share = oc.share_file_with_link(cloud_file).get_link()
print(share)

basename_noext = os.path.splitext(basename)[0]

print(f"[url={share}]{basename_noext}[/url]")


# GUI output
master = tk.Tk()
pos_x = int(master.winfo_screenwidth() / 2 - 400)
pos_y = int(master.winfo_screenheight() / 2)
master.wm_geometry(f"800x50+{pos_x}+{pos_y}")
w = tk.Text(master, height=1, exportselection=1)
w.insert(1.0, f"[url={share}]{basename_noext}[/url]")
w.tag_add(SEL, "1.0", END)
w.mark_set(INSERT, "1.0")
w.see(INSERT)
w.pack(fill=tk.BOTH, expand=1)
master.mainloop()
