# smToDodo: build with Python 3.11.5, Simfile 2.1.1 and pydub 0.25.1
import simfile
import json, re, argparse, configparser
from simfile.timing import Beat, TimingData
from simfile.notes import NoteData, NoteType
from simfile.notes.group import group_notes, NoteWithTail, Note
from simfile.timing.engine import TimingEngine
from pydub import AudioSegment
from pathlib import Path
from itertools import count
from shutil import rmtree

__version__ = "1.0"

### Argument / Config parsing and checking ### 

parser = argparse.ArgumentParser()
parser.add_argument("simfile_path", help = "the path of the simfile you want to convert", type = Path)
parser.add_argument("-hs", "--hitsounds", help = "enables hitsounding on all charts", action = "store_true")
parser.add_argument("-na", "--noAutoAdd", help = "disables adding the song to the song selection automatically", action = "store_true")
parser.add_argument("-c", "--config", help = "the path of the config file (defaults to smToDodo.ini)", type = Path, default="smToDodo.ini")
parser.add_argument("-v", "--version", action = "version", version = f"smToDodo v{__version__}")
args = parser.parse_args()

config = configparser.ConfigParser()
config.read(args.config)
if config["DEFAULT"]["SongsPath"]:
    songs_path = Path(config["DEFAULT"]["SongsPath"])
else:
    print("ERROR: You haven't set the song path in the config! Please add your song path in the config.")
    raise SystemExit

if args.simfile_path.is_file():
    try:
        stepfile = simfile.open(args.simfile_path)
    except FileNotFoundError:
        print("ERROR: The simfile path isn't a valid simfile!")
        raise SystemExit
else:
    try:
        stepfile = simfile.open(next(args.simfile_path.glob("*.ssc")))
    except StopIteration:
        try:
            stepfile = simfile.open(next(args.simfile_path.glob("*.sm")))
        except StopIteration:
            print("ERROR: The simfile path doesn't contain a valid simfile!")
            raise SystemExit

if not songs_path.is_dir():
    print("ERROR: The songs path isn't a valid folder!")
    raise SystemExit


### Constants and helper functions ### 

categories = ["AuxPercussion", "Bass", "CounterMelody", "Drums", "Harmony", "Melody", "Signature"]

def mapTemplate():
    beatmap = {
        "slug": None,
        "type": "Discrete",
        "category": None,
        "difficulty": None,
        "instruments": [],
        "instrumentRequirements": [],
        "events": [],
        "inputs": [],
        "laneCount": None
    }
    return beatmap

def diffToNum(diff):
    if diff == "Beginner":
        return 1
    elif diff == "Easy":
        return 2
    elif diff == "Medium":
        return 3
    elif diff == "Hard":
        return 4
    elif diff in ("Challenge", "Edit"):
        return 5

def hitsounding(edit):
    if args.hitsounds:
        if edit:
            return [{"start": 0, "duration": config["Instruments"]["InstNormalDuration"], "note": config["Instruments"]["InstNormalNote"]}]
        else:
            return [{"start": 0, "duration": config["Instruments"]["InstEditDuration"], "note": config["Instruments"]["InstEditNote"]}]
    else:
        return []

def musicDuration():
    return int(music.duration_seconds * 1000)

def t(b): # beat to time
    return int(str(engine.time_at(Beat(b))).replace(".",""))

def r(s): # apply regex on string that removes non alphanumeric characters
    return re.sub(r"\W+", "", s, flags = re.A)


### General info ###

output = {
    "slug": None,
    "composer": None,
    "duration": None,
    "bucket": "Custom",
    "scaleKey": "a",
    "scaleType": "minor",
    "guideStartOffset": 0,
    "guide": [],
    "beatmaps": [],
    "preferredAssignments": [],
}
engine = TimingEngine(TimingData(stepfile))
if args.simfile_path.is_file():
    music = AudioSegment.from_file(args.simfile_path.parent.joinpath(stepfile.music))
else:
    music = AudioSegment.from_file(args.simfile_path.joinpath(stepfile.music))

output["slug"] = f"{r(stepfile.titletranslit if stepfile.titletranslit else stepfile.title)}-{r(stepfile.artisttranslit if stepfile.artisttranslit else stepfile.artist)}".lower()
if args.hitsounds:
    output["slug"] += "-hitsounded"
output["composer"] = stepfile.artisttranslit if stepfile.artisttranslit else stepfile.artist
if config["Annotation"]["AuthorAnno"]:
    output["composer"] += f" {config['Annotation']['AuthorAnno']}"
output["duration"] = musicDuration()


### Guides ###

for i in count(start = 0, step = 4):
    if t(i) > output["duration"]:
        break
    output["guide"].append([t(i), t(i+1), t(i+2), t(i+3)])


### Beatmaps ###

slugs = []
duplicates = 0
for slot, chart in enumerate(stepfile.charts):

    ### Slot and duplicate managment ###

    slot = slot - duplicates
    if slot > 6:
        print("WARNING: Your simfile has more than 7 charts! Dodo Re Mi only supports 7 charts per song. A folder will still be generated, but some of the charts might be missing.")
        print(f"    Here are the IDs of the generated charts: {slugs}")
        break

    slug = f"{r(chart.stepstype)}-{chart.difficulty}{chart.meter}-{r(chart.description)}".lower()
    if slug in slugs:
        print("WARNING: Your simfile has two charts that generated the same ID! This means they are equal in steps type, difficulty, meter and description. The duplicate will be skipped.")
        print(f"    Here is the ID of the duplicate: {slug}")
        duplicates += 1
        continue

    slugs.append(slug)


    ### General settings ###

    engine = TimingEngine(TimingData(stepfile, chart))

    beatmap = mapTemplate()
    beatmap["slug"] = slug
    beatmap["category"] = categories[slot] 
    beatmap["difficulty"] = diffToNum(chart.difficulty)

    instrument = config["Instruments"]["InstEditName"] if chart.difficulty == "Edit" else config["Instruments"]["InstNormalName"]
    beatmap["instruments"].append(instrument)


    ### Notedata processing ###

    maxColumn = 0
    notedata = group_notes(NoteData(chart), join_heads_to_tails=True)
    for n in notedata:
        n = n[0]
        if type(n) == Note:
            if n.note_type != NoteType.TAP:
                continue
        if n.column > 5:
            maxColumn = 6
            continue
        if not engine.hittable(n.beat):
            continue
        
        input = {"start": t(n.beat), "lanes": [n.column], "notes": hitsounding(chart.difficulty == "Edit")}
        if type(n) == NoteWithTail:
            input["duration"] = t(n.tail_beat) - t(n.beat)
        
        beatmap["inputs"].append(input)

        maxColumn = max(maxColumn, n.column)


    ### Adding to output ###

    if maxColumn > 5:
        print("WARNING: Your simfile has a chart that has more than 6 columns! Dodo Re Mi only supports 6 lanes per chart. The chart will still be added, but notes in lanes above the sixth have been discarded.")
        print(f"    Here is the ID of the relevant chart: {slug}")
        maxColumn = 5
    beatmap["laneCount"] = maxColumn + 1

    output["beatmaps"].append(beatmap)
    output["preferredAssignments"].append([beatmap["slug"], instrument])


### Edgecase handling ###

earliest_note, latest_note = None, None
for b in output["beatmaps"]:
    earliest_note = min(b["inputs"][0]["start"], earliest_note) if earliest_note != None else b["inputs"][0]["start"]
    latest_note = max(b["inputs"][-1]["start"], latest_note) if latest_note != None else b["inputs"][-1]["start"]

# How long a song plays seems to depend on the music file length, NOT the duration set
# So I'm expanding the music file if there are notes after the music file ended (that shouldn't happen but just to make sure)
if latest_note >= musicDuration():
    music = music + AudioSegment.silent(duration = latest_note - musicDuration() + 1)

# Notes before 3 seconds do not appear because the web client tries to let them appear before 0ms
# I tried working with guideStartOffset, but that didn't really work
# So I'm moving all notes to 3001ms and compensating by adding silence to the music file
if earliest_note <= 3000:
    offset = 3001 - earliest_note
    music = AudioSegment.silent(duration = offset) + music

    for beatmap in output["beatmaps"]:
        for input in beatmap["inputs"]:
            input["start"] += offset
    for subguides in output["guide"]:
        for i, _ in enumerate(subguides):
            subguides[i] += offset

output["duration"] = musicDuration()


### Exporting folder ###

if Path(songs_path.joinpath(output["slug"])).exists():
    rmtree(songs_path.joinpath(output["slug"]))
Path(songs_path.joinpath(output["slug"])).mkdir()

music.export(songs_path.joinpath(f"{output['slug']}/backing.ogg"), format = "ogg")

with open(songs_path.joinpath(f"{output['slug']}/config.json"), "w", encoding = "utf8") as file:
    json.dump(output, file, indent = 4, ensure_ascii = False)

title = {"TITLE": stepfile.titletranslit if stepfile.titletranslit else stepfile.title}
if args.hitsounds:
    title["TITLE"] += f" {config['Annotation']['HasHitsoundsAnno']}" or ""
else:
    title["TITLE"] += f" {config['Annotation']['NoHitsoundsAnno']}"  or ""
for lang in ["de", "en", "es", "es-XL", "fr", "it"]:
    with open(songs_path.joinpath(f"{output['slug']}/{lang}.json"), "w", encoding = "utf8") as file:
        json.dump(title, file, indent = 4, ensure_ascii = False)

print(f"INFO: The folder has been generated! Here is the ID: {output['slug']}")
if args.noAutoAdd:
    print(f"    In order to add the song to the game, you will need to add that ID in the songs.json file of the game.")
else:
    with open(songs_path.joinpath("songs.json"), "r+", encoding = "utf8") as file:
        songs = json.load(file)
        if output["slug"] not in songs:
            songs.append(output["slug"])
            file.seek(0)
            json.dump(songs, file, indent = 4)