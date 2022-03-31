import pprint
import requests
import time
import glob
import os
import random
import json
from collections import defaultdict, Counter
from core import face, util

GALLERY_PATH = "./images/gallery/"
FACESET = "myt_val_ok2"
EMOTIONS = {"sad": "sadness", "happy": "happiness", "neutral": "neutral"}
GESTURES = {"open": "hand_open", "up": "thumb_up", "down": "thumb_down", "finger": "index_finger_up",
            "victory": "victory", "fist": "fist"}


def test_face_detection():
    faces = glob.glob(GALLERY_PATH + "*sad*")\
            + glob.glob(GALLERY_PATH + "*neutral*")\
            + glob.glob(GALLERY_PATH + "*happy*")
    print("len faces 1", len(faces))
    random.shuffle(faces)
    correct_emotions = 0
    correct_matches = 0
    false_alarms = 0
    tokens = defaultdict(list)
    rev_tokens = dict()

    for f in faces:
        gt_user, gt_emotion0 = os.path.splitext(os.path.basename(f))[0].split("_")[0:2]
        gt_emotion = EMOTIONS[gt_emotion0]
        face_token, smile, emotion = face.detect(f)
        tokens[gt_user] += [face_token]
        rev_tokens[face_token] = gt_user
        if gt_emotion == emotion:
            correct_emotions += 1
        print(f"{gt_user},{gt_emotion},{emotion}")
        time.sleep(1.1)

    print("len tokens:", len(tokens))

    genuine = list(tokens.keys())[:25]
    impostors = list(tokens.keys())[25:]
    n_genuine = 0
    n_impostors = 0

    print("genuine:", len(genuine), "- impostors:", len(impostors))

    # enrolling genuine users
    for user in genuine:
        gallery = tokens[user][:2]
        for g in gallery:
            face.faceset([g], FACESET)
            time.sleep(1.1)

    # trying to log genuine users
    for user in genuine:
        gallery = tokens[user][:2]
        probe = tokens[user][2:]
        for p in probe:
            n_genuine += 1
            match = face.search(p, FACESET)
            if match in gallery:
                correct_matches += 1
                print("correct match")
            else:
                print(f"False reject: {user} mistaken for {rev_tokens[match]}.")
            time.sleep(1.1)

    # trying to log impostor users
    for user in impostors:
        for p in tokens[user]:
            n_impostors += 1
            match = face.search(p, FACESET)
            if match is not None:
                false_alarms += 1
                print(f"false_alarm: {user} mistaken for {rev_tokens[match]}.")
            time.sleep(1.1)

    print(f"\n\nfaces: {len(faces)}, n_genuine: {n_genuine}, n_impostors: {n_impostors};")
    print(f"Correct emotions (accuracy): {correct_emotions}/{len(faces)}: {correct_emotions/len(faces)};")
    print(f"Correct matches (DIR): {correct_matches}/{n_genuine}: {correct_matches/n_genuine};")
    print(f"FRR: {1 - correct_matches/n_genuine};")
    print(f"FAR: {false_alarms}/{n_impostors}: {false_alarms/n_impostors}.")


def test_gesture_detection():
    url = 'https://api-us.faceplusplus.com/humanbodypp/v1/gesture'
    pictures = []
    num_hands = 0
    correct_gestures = 0
    gestures_count = defaultdict(list)

    for g in GESTURES:
        pictures += glob.glob(GALLERY_PATH + f"*{g}*")
    print("len pictures 1", len(pictures))

    # random.shuffle(pictures)  # debug
    # pictures = pictures[:10]  # debug
    # print("len pictures 2", len(pictures))

    for p in pictures:
        gt_user, gt_gesture0 = os.path.splitext(os.path.basename(p))[0].split("_")[0:2]
        gt_gesture = GESTURES[gt_gesture0]

        files = {
            'api_key': (None, util.get_property("gest_api_key")),
            'api_secret': (None, util.get_property("gest_api_secret")),
            'image_file': (p, open(p, 'rb')),
            'return_gesture': (None, '1'),
        }
        x = requests.post(url, files=files)
        hands = json.loads(x.text)['hands']
        for h in hands:
            num_hands += 1
            gesture = Counter(h["gesture"]).most_common(1)[0][0]
            gestures_count[gt_gesture] += [gesture]
            if gt_gesture == gesture:
                correct_gestures += 1
            print(f"{gt_user},{gt_gesture},{gesture}")

        time.sleep(1.1)

    gestures_matrix = dict()
    for g in gestures_count:
        gestures_matrix[g] = Counter(gestures_count[g])

    print("num hands:", num_hands)
    print(f"Correct gestures (accuracy): {correct_gestures}/{len(pictures)}: {correct_gestures / len(pictures)};")
    pprint.pprint(gestures_matrix)


if __name__ == '__main__':
    # test_face_detection()
    test_gesture_detection()
