import gi
import time
import hashlib
import cv2 as cv
from core import face

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
from psycopg2.errors import UniqueViolation
from core import util

ENTER = 65293


class LoginBox(Gtk.Box):
    def __init__(self, window, mainBox, infoLabel):
        Gtk.Box.__init__(self)
        self.mainBox = mainBox
        self.infoLabel = infoLabel
        self.window = window

        # Login
        self.username_label = Gtk.Label("Username")
        mainBox.pack_start(self.username_label, True, True, 0)
        self.username_entry = Gtk.Entry()
        self.username_entry.set_placeholder_text("Insert your username")
        mainBox.pack_start(self.username_entry, True, True, 0)

        self.password_label = Gtk.Label("Password")
        mainBox.pack_start(self.password_label, True, True, 0)
        self.password_entry = Gtk.Entry()
        self.password_entry.set_visibility(False)
        self.password_entry.set_placeholder_text("Insert your password")
        mainBox.pack_start(self.password_entry, True, True, 0)

        self.login_button = Gtk.Button.new_with_label("Login")
        self.login_button.connect('clicked', self.login)
        mainBox.pack_start(self.login_button, True, True, 0)

        self.register_button = Gtk.Button.new_with_label("Register")
        self.register_button.connect('clicked', self.register_dialog)
        mainBox.pack_start(self.register_button, True, True, 0)

    def login(self, button):
        user = self.username_entry.get_text()
        psw = hashlib.sha256(self.password_entry.get_text().encode()).hexdigest()
        query = f"SELECT username, deaf FROM users WHERE username='{user}' AND psw='{psw}';"
        users = util.execute_query(query).fetchall()

        if len(users) == 1:
            deaf = users[0][1]
            print("login deaf:", deaf)
            img = util.get_last_pic("opencv_frame")
            face_token, _, emotion = face.detect(img)
            go_to_playlist(self, user, deaf, emotion)
        else:
            self.infoLabel.set_markup("<span foreground='red'><b>Wrong credentials.</b></span>")

    def register_dialog(self, button):
        self.window.can_register = False
        dialog = RegistrationDialog(self)
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            print("The REGISTER button was clicked")
            dialog.register(button)
        elif response == Gtk.ResponseType.CANCEL:
            print("The Cancel button was clicked")

        dialog.destroy()

    def show(self, window):
        window.show_all()
        self.username_entry.grab_focus()

    def hide(self):
        self.username_label.hide()
        self.username_entry.hide()
        self.password_label.hide()
        self.password_entry.hide()
        self.login_button.hide()
        self.register_button.hide()

    def keyPressed(self, widget, event, data=None):
        key = event.keyval

        if key == ENTER:
            self.login(self.login_button)


class RegistrationDialog(Gtk.Dialog):
    def __init__(self, parent):
        Gtk.Dialog.__init__(self, title="Registration", transient_for=parent.window, flags=0)
        self.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK
        )

        self.set_default_size(520, 100)
        self.parent = parent

        box = self.get_content_area()

        self.label = Gtk.Label(label="Insert your data and then wait until 3 pictures are taken!")
        box.add(self.label)

        # Registration
        self.new_username_label = Gtk.Label("\nNew Username")
        box.add(self.new_username_label)
        self.new_username_entry = Gtk.Entry()
        self.new_username_entry.set_placeholder_text("Insert your desired username")
        box.add(self.new_username_entry)

        self.new_password_label = Gtk.Label("New Password")
        box.add(self.new_password_label)
        self.new_password_entry = Gtk.Entry()
        self.new_password_entry.set_visibility(False)
        self.new_password_entry.set_placeholder_text("Insert your desired password")
        box.add(self.new_password_entry)

        self.deaf = Gtk.CheckButton("Deaf user   ")
        box.add(self.deaf)

        self.show_all()

    def register(self, button):
        user = self.new_username_entry.get_text()
        psw = hashlib.sha256(self.new_password_entry.get_text().encode()).hexdigest()
        face_tokens = []
        emotions = []

        for i in range(3):
            if i > 0:
                time.sleep(1.11)
            img_name = util.get_last_pic("frame")
            face_token, _, emotion = face.detect(img_name)
            print("emotion:", emotion)
            face_tokens.append(face_token)
            emotions.append(emotion)
            GLib.idle_add(self.label.set_text, f"Thank you, picture number {i + 1} taken!")

        face.faceset(face_tokens)
        face_tokens = [hashlib.sha256(token.encode()).hexdigest() for token in face_tokens]
        face_tokens = ",".join(face_tokens)

        query = f"INSERT INTO users(username, psw, deaf, faces) VALUES ('{user}', '{psw}', {self.deaf.get_active()}, '{face_tokens}'); "
        try:
            util.execute_query(query)
            go_to_playlist(self.parent, user, self.deaf.get_active(), emotions[0])
        except UniqueViolation:
            self.new_username_entry.set_text("")
            self.new_password_entry.set_text("")
            self.label.set_text("The selected Username already exists.")


def go_to_playlist(parent, user, deaf, emotion):
    playlists = {
        True: {
            "sadness": "https://www.youtube.com/playlist?list=PLMzUXFpWgSFGvY75HUQ_nWaA1uT5QZPxh",
            "happiness": "https://www.youtube.com/playlist?list=PLMzUXFpWgSFEgSpsBQ-T6WtbsUtmmf10E",
            "neutral": "https://www.youtube.com/playlist?list=PLMzUXFpWgSFEqY1Ff0NJFZ5BGLwMmi9hm"
        },
        False: {
            "sadness": "https://www.youtube.com/playlist?list=PLih-wODrJ8UFotsjk4cUW1P06EzpEXNRY",
            "happiness": "https://www.youtube.com/playlist?list=PLih-wODrJ8UHcl5rrlG6Tq3VCQHr8spwI",
            "neutral": "https://www.youtube.com/playlist?list=PLih-wODrJ8UFhWWkMdGxzdAEJqCE25FDD"
        }
    }

    parent.infoLabel.set_text(f"Welcome {user}.")
    playlist = playlists[deaf][emotion] if emotion in playlists[deaf] else playlists[deaf]["neutral"]
    parent.window.youtube.entry.set_text(playlist)
    parent.window.youtube.show_button(parent.window)
    parent.hide()
    parent.window.youtube.play(None)
