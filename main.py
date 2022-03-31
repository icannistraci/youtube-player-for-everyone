#!/usr/bin/python3

import hashlib
import shlex
import time
import threading
import json
import subprocess
from collections import Counter
import requests
import gi
import vlc
import cv2 as cv
import gphoto2 as gp
import azure.cognitiveservices.speech as speechsdk

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from core import youtubeplayer, login, util, face

instance = vlc.Instance('--no-xlib')

DELAY = 1.1


class MainWindow(Gtk.Window):
    def __init__(self):
        # Metadata
        self.title = "Multimodal YouTubePlayer"
        Gtk.Window.__init__(self)
        self.set_size_request(520, 100)

        # Title bar tweaks
        headerBar = Gtk.HeaderBar()
        headerBar.set_show_close_button(True)
        self.set_titlebar(headerBar)
        self.set_resizable(False)

        # Main Box: All widgets are inside this
        mainBox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        mainBox.set_property('margin', 10)
        mainBox.set_size_request(400, 100)

        # Title
        self.infoLabel = Gtk.Label(label="A YouTubePlayer for Everyone")
        self.infoLabel.set_line_wrap(True)
        mainBox.pack_start(self.infoLabel, True, True, 0)

        # Login
        self.login = login.LoginBox(self, mainBox, self.infoLabel)
        mainBox.pack_start(self.login, True, True, 0)
        self.login.show(self)

        # YouTube
        self.youtube = youtubeplayer.YouTubePlayer(self, mainBox, headerBar, self.infoLabel)
        self.youtube.show(self)

        # Check if registration button clicked
        self.can_register = True

        # Init webcam monitoring
        self.running_web = True
        camera = gp.Camera()
        try:
            text = str(camera.get_summary())
            if "Nessuna fotocamera" in text or "No Image Capture" in text:
                self.thread_web = threading.Thread(target=self.web_capture)
            else:
                self.thread_web = threading.Thread(target=self.cam_capture)
        except:
            self.thread_web = threading.Thread(target=self.web_capture)

        self.thread_web.start()

        # Init microphone monitoring
        self.running_mic = True
        self.thread_mic = threading.Thread(target=self.mic_capture)
        self.thread_mic.start()

    def keyPressed(self, widget, event, data=None):
        if self.youtube.entry.is_visible():
            self.youtube.keyPressed(widget, event, data)
        elif self.login.login_button.is_visible():
            self.login.keyPressed(widget, event, data)

    def web_capture(self):
        time.sleep(3)
        print("start web capture")
        cam = cv.VideoCapture(0)
        img_counter = 0
        ts = time.time()
        while self.running_web:
            ret = cam.grab()
            if not ret:
                print("failed to grab frame")
                continue
            if time.time() - ts >= DELAY:
                ret, frame = cam.retrieve()
                if not ret:
                    print("failed to retrieve frame")
                    continue

                img_name = f"images/test-img/frame_{img_counter}.png"
                cv.imwrite(img_name, frame)
                print(ts, f"{img_name} written!")

                if self.youtube.entry.is_visible():
                    url = 'https://api-us.faceplusplus.com/humanbodypp/v1/gesture'
                    files = {
                        'api_key': (None, util.get_property("gest_api_key")),
                        'api_secret': (None, util.get_property("gest_api_secret")),
                        'image_file': (img_name, open(img_name, 'rb')),
                        'return_gesture': (None, '1'),
                    }
                    x = requests.post(url, files=files)
                    hands = json.loads(x.text)['hands']
                    print("hands:", hands)
                    for h in hands:
                        gesture = Counter(h["gesture"]).most_common(1)[0][0]
                        if gesture == "hand_open":
                            print(gesture, "-> pause")
                            t = self.youtube.entry.get_text()
                            if t == ' ' or t == '':
                                self.youtube.entry.set_text("")
                                GLib.idle_add(self.youtube.play, None)
                                self.show_info("Play/Pause")
                        elif gesture == "index_finger_up":
                            print(gesture, "-> next song")
                            GLib.idle_add(self.youtube.next, None)
                            self.show_info("Next")
                        elif gesture == "victory" or gesture == "double_finger_up":
                            print(gesture, "-> previous song")
                            GLib.idle_add(self.youtube.previous, None)
                            self.show_info("Previous")
                        elif gesture == "thumb_up":
                            print(gesture, "-> volume up")
                            GLib.idle_add(self.youtube.volume_up, None)
                            self.show_info("Volume up")
                        elif gesture == "thumb_down":
                            print(gesture, "-> volume down")
                            GLib.idle_add(self.youtube.volume_down, None)
                            self.show_info("Volume down")
                        elif gesture == "fist":
                            print(gesture, "-> mute")
                            GLib.idle_add(self.youtube.toggle_mute, None)
                            self.show_info("Mute")
                        else:
                            print(gesture, "-> nothing")

                elif self.can_register:
                    try:
                        face_token, smile, emotion = face.detect(img_name)
                        if face_token is None:
                            continue
                        print("emotion:", emotion)
                    except:
                        GLib.idle_add(self.infoLabel.set_text, "Face detection error.")
                        continue
                    match = face.search(face_token)
                    if match is None:
                        continue
                    print("match:", match)
                    match = hashlib.sha256(match.encode()).hexdigest()
                    cursor = util.execute_query(f"SELECT username, deaf FROM users WHERE faces LIKE '%{match}%';")
                    res = cursor.fetchall()
                    user = res[0][0]
                    deaf = res[0][1]
                    print("res:", user, deaf)

                    # Login
                    login.go_to_playlist(self.login, user, deaf, emotion)

                img_counter += 1
                ts = time.time()

    def cam_capture(self):
        time.sleep(3)
        print("start web capture")
        img_counter = 0
        while self.running_web:
            img_name = f"images/test-img/frame_{img_counter}.jpg"
            cmd = f"gphoto2 --capture-image-and-download --filename {img_name} --force-overwrite"
            args = shlex.split(cmd)
            s = subprocess.Popen(args, stderr=subprocess.PIPE)
            s.wait()
            err = s.stderr.read()

            if len(err) != 0:
                print("failed to take picture")
                continue
            else:
                img_counter += 1
                print(f"{img_name} written!", "\n", s.stdout)

                if self.youtube.entry.is_visible():
                    url = 'https://api-us.faceplusplus.com/humanbodypp/v1/gesture'
                    files = {
                        'api_key': (None, util.get_property("gest_api_key")),
                        'api_secret': (None, util.get_property("gest_api_secret")),
                        'image_file': (img_name, open(img_name, 'rb')),
                        'return_gesture': (None, '1'),
                    }
                    x = requests.post(url, files=files)
                    hands = json.loads(x.text)['hands']
                    print("hands:", hands)
                    for h in hands:
                        gesture = Counter(h["gesture"]).most_common(1)[0][0]
                        if gesture == "hand_open":
                            print(gesture, "-> pause")
                            t = self.youtube.entry.get_text()
                            if t == ' ' or t == '':
                                self.youtube.entry.set_text("")
                                GLib.idle_add(self.youtube.play, None)
                                self.show_info("Play/Pause")
                        elif gesture == "index_finger_up":
                            print(gesture, "-> next song")
                            GLib.idle_add(self.youtube.next, None)
                            self.show_info("Next")
                        elif gesture == "victory" or gesture == "double_finger_up":
                            print(gesture, "-> previous song")
                            GLib.idle_add(self.youtube.previous, None)
                            self.show_info("Previous")
                        elif gesture == "thumb_up":
                            print(gesture, "-> volume up")
                            GLib.idle_add(self.youtube.volume_up, None)
                            self.show_info("Volume up")
                        elif gesture == "thumb_down":
                            print(gesture, "-> volume down")
                            GLib.idle_add(self.youtube.volume_down, None)
                            self.show_info("Volume down")
                        elif gesture == "fist":
                            print(gesture, "-> mute")
                            GLib.idle_add(self.youtube.toggle_mute, None)
                            self.show_info("Mute")
                        else:
                            print(gesture, "-> nothing")

                elif self.can_register:
                    try:
                        face_token, smile, emotion = face.detect(img_name)
                        if face_token is None:
                            continue
                        print("emotion:", emotion)
                    except:
                        GLib.idle_add(self.infoLabel.set_text, "Face detection error.")
                        continue
                    match = face.search(face_token)
                    if match is None:
                        continue
                    print("match:", match)
                    match = hashlib.sha256(match.encode()).hexdigest()
                    cursor = util.execute_query(f"SELECT username, deaf FROM users WHERE faces LIKE '%{match}%';")
                    res = cursor.fetchall()
                    user = res[0][0]
                    deaf = res[0][1]
                    print("res:", user, deaf)

                    # Login
                    login.go_to_playlist(self.login, user, deaf, emotion)
                time.sleep(DELAY)

    def mic_capture(self):
        print(" & start mic capture")

        def stop_cb(evt):
            print('CLOSING on {}'.format(evt))
            self.running_mic = False

        def handle_event(evt):
            if evt.result.text == "play":
                print(evt.result.text, "-> play")
                GLib.idle_add(self.youtube.play, None)
                self.show_info("Play")
            elif evt.result.text == "stop" or evt.result.text == "pause":
                print(evt.result.text, "-> stop/pause")
                GLib.idle_add(self.youtube.play, None)
                self.show_info("Pause")
            elif evt.result.text == "next" or evt.result.text == "skip":
                print(evt.result.text, "-> next song")
                GLib.idle_add(self.youtube.next, None)
                self.show_info("Next")
            elif evt.result.text == "previous":
                print(evt.result.text, "-> previous song")
                GLib.idle_add(self.youtube.previous, None)
                self.show_info("Previous")
            elif "up" in evt.result.text:
                print(evt.result.text, "-> volume up")
                GLib.idle_add(self.youtube.volume_up, None)
                self.show_info("Volume up")
            elif "down" in evt.result.text:
                print(evt.result.text, "-> volume down")
                GLib.idle_add(self.youtube.volume_down, None)
                self.show_info("Volume down")
            elif "mute" in evt.result.text:
                print(evt.result.text, "-> mute")
                GLib.idle_add(self.youtube.toggle_mute, None)
                self.show_info("Mute/Unmute")
            else:
                print(evt.result.text, "-> nothing")

        speech_config = speechsdk.SpeechConfig(subscription=util.get_property("speech_key_1"),
                                               region=util.get_property("service_region"))
        speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config)
        speech_recognizer.recognizing.connect(handle_event)

        speech_recognizer.session_started.connect(lambda evt: print('SESSION STARTED: {}'.format(evt)))
        speech_recognizer.session_stopped.connect(lambda evt: print('SESSION STOPPED {}'.format(evt)))
        speech_recognizer.canceled.connect(lambda evt: print('CANCELED {}'.format(evt)))

        # stop continuous recognition on either session stopped or canceled events
        speech_recognizer.session_stopped.connect(stop_cb)
        speech_recognizer.canceled.connect(stop_cb)

        # Start continuous speech recognition
        speech_recognizer.start_continuous_recognition()
        while self.running_mic:
            # print("mic sleep")
            time.sleep(.5)

    def show_info(self, text):
        # def _show_info():
        #     t = self.infoLabel.get_text()
        #     GLib.idle_add(self.infoLabel.set_markup, f"<b>{text}</b>")
        #     time.sleep(3)
        #     GLib.idle_add(self.infoLabel.set_text, t)
        #
        # threading.Thread(target=_show_info).start()
        t = self.infoLabel.get_text()
        GLib.idle_add(self.infoLabel.set_markup, f"<b>{text}</b>")
        time.sleep(3)
        GLib.idle_add(self.infoLabel.set_text, t)

    def quit(self, widget=None, *data):
        self.running_mic = False
        self.running_web = False
        self.thread_mic.join()
        self.thread_web.join()
        Gtk.main_quit()


if not util.check_db():
    print("creating DB...")
    util.create_db()

window = MainWindow()
window.set_icon_from_file('images/icons/youtube.svg')
window.connect('key-release-event', window.keyPressed)
window.connect('delete-event', window.quit)
window.login.username_entry.grab_focus()

Gtk.main()
