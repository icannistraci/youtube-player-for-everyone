import glob
import os
import urllib
import json
import ctypes
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

if "core" in os.getcwd():
    os.chdir("..")
CONFIG_FILE = "data.json"


def get_property(property):
    with open(CONFIG_FILE, 'r') as f:
        data = json.load(f)
        return data[property]


API_KEY = get_property("yt_api_key")
DB_NAME = get_property("psql_db")


def _getYTResultURL(query):
    url = 'https://www.googleapis.com/youtube/v3/search?type=video&part=snippet&'
    t = urllib.parse.urlencode({"q": query})
    url += t + '&'
    t = urllib.parse.urlencode({"key": API_KEY})
    url += t

    try:
        response = urllib.request.urlopen(url)

    except urllib.error.URLError:
        return -1

    data = json.loads(response.read())
    search_results = []

    for x in data['items']:
        d = dict()
        d['id'] = x['id']['videoId']
        d['title'] = x['snippet']['title']
        search_results.append(d)

    return search_results


def _getYTResultURL_PL(query):
    url = 'https://www.googleapis.com/youtube/v3/search?type=playlist&part=snippet&'
    t = urllib.parse.urlencode({"q": query})
    url += t + '&'
    t = urllib.parse.urlencode({"key": API_KEY})
    url += t

    try:
        response = urllib.request.urlopen(url)

    except urllib.error.URLError:
        return -1

    data = json.loads(response.read())
    search_results = []

    for x in data['items']:
        d = dict()
        d['id'] = x['id']['playlistId']
        d['title'] = x['snippet']['title']
        search_results.append(d)

    return search_results


def writeToConfig(data):
    f = open('.config', 'w')
    data = json.dumps(data)
    f.write(data)
    f.close()
    return


def readFromConfig():
    f = open('.config', 'r')
    data = f.read()
    data = json.loads(data)
    f.close()
    return data


def get_window_pointer(window):
    """ Use the window.__gpointer__ PyCapsule to get the C void* pointer to the window.
        From https://github.com/oaubert/python-vlc/blob/master/examples/gtkvlc.py."""
    ctypes.pythonapi.PyCapsule_GetPointer.restype = ctypes.c_void_p
    ctypes.pythonapi.PyCapsule_GetPointer.argtypes = [ctypes.py_object]
    return ctypes.pythonapi.PyCapsule_GetPointer(window.__gpointer__, None)


class SearchBox(Gtk.Frame):
    def __init__(self, ytid='', title=''):
        Gtk.Frame.__init__(self)
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        self.set_size_request(450, 30)
        self.add(self.box)
        self.ytid = ytid

        self.title = Gtk.Label(title)
        self.title.set_xalign(0.01)
        self.title.set_line_wrap(True)
        self.img = ytid

        self.box.pack_start(self.title, True, True, 0)

    def setTitleAndId(self, title, ytid):
        self.title.set_text(title)
        self.ytid = ytid


def execute_query(query, db=DB_NAME):
    psql_user = get_property("psql_user")
    psql_psw = get_property("psql_password")
    host = get_property("psql_host")
    port = get_property("psql_port")
    host_name = "" if host == "" else f" host='{host}'"
    port_name = "" if port == "" else f" host='{port}'"
    db_name = "" if db == "" else f" dbname='{db}'"
    con = psycopg2.connect(f"user={psql_user} password='{psql_psw}'{db_name}{host_name}{port_name}")
    con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = con.cursor()
    cursor.execute(query)
    return cursor


def create_db():
    query = f"CREATE DATABASE {DB_NAME};"
    execute_query(query, db="")
    query = "CREATE TABLE users (id serial PRIMARY KEY, username varchar not null unique, psw varchar not null, deaf boolean, faces text);"
    execute_query(query)


def check_db():
    cur = execute_query("SELECT datname FROM pg_database;", db="")
    list_database = cur.fetchall()
    return (DB_NAME,) in list_database


def get_last_pic(pattern):
    imgs = glob.glob(f"images/test-img/{pattern}_*")
    last_img = ""
    last_ts = 0
    for img in imgs:
        ts = os.path.getmtime(img)
        if ts > last_ts:
            last_img = img
            last_ts = ts
    return last_img
