import base64
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

import musiclibrary
from client import ask_ollama
import speech_recognition as sr

MICROPHONE_INDEX = 14

WEBSITES = {
    "Google": ("https://www.google.com", ("google",)),
    "Instagram": ("https://www.instagram.com", ("instagram", "insta")),
    "Facebook": ("https://www.facebook.com", ("facebook",)),
    "YouTube": ("https://www.youtube.com", ("youtube", "you tube")),
    "LinkedIn": ("https://www.linkedin.com", ("linkedin", "linked in", "linkdin")),
    "GitHub": ("https://github.com", ("github", "git hub")),
    "LeetCode": ("https://leetcode.com", ("leetcode", "leet code")),
    "ChatGPT": ("https://chatgpt.com", ("chatgpt", "chat gpt")),
    "Claude": ("https://claude.ai", ("claude",)),
    "WhatsApp": ("https://web.whatsapp.com", ("whatsapp", "what s app", "what app")),
}

APPS = {
    "calculator": ("Calculator", "calc.exe", ()),
    "notepad": ("Notepad", "notepad.exe", ()),
    "paint": ("Paint", "mspaint.exe", ()),
    "file explorer": ("File Explorer", "explorer.exe", ("explorer",)),
    "browser": ("your default browser", None, ("web browser",)),
    "word": ("Microsoft Word", "WINWORD.EXE", ("ms word", "microsoft word")),
    "excel": ("Microsoft Excel", "EXCEL.EXE", ("ms excel", "microsoft excel")),
}

def speak(message):
    encoded_message = base64.b64encode(message.encode("utf-16le")).decode("ascii")
    script = (
        "Add-Type -AssemblyName System.Speech; "
        "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$speaker.Volume = 100; "
        f"$text = [Text.Encoding]::Unicode.GetString("
        f"[Convert]::FromBase64String('{encoded_message}')); "
        "$speaker.Speak($text); "
        "$speaker.Dispose()"
    )
    try:
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        print(f"Windows speech error: {error}")


def speak_news(stories):
    speak(f"I found {len(stories)} news stories. Here they are.")
    for number, (title, details) in enumerate(stories, start=1):
        story = f"Story {number}. {title}."
        if details:
            story += f" {details}"
        else:
            story += " No summary was provided."
        speak(story)


def clean_words(text):
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def get_news_api_key():
    api_key = os.getenv("NEWS_API_KEY")
    if api_key:
        return api_key

    env_file = Path(__file__).with_name(".env")
    if not env_file.exists():
        return ""

    for line in env_file.read_text(encoding="utf-8").splitlines():
        name, separator, value = line.partition("=")
        if separator and name.strip() == "NEWS_API_KEY":
            return value.strip().strip("\"'")
    return ""


def tell_news():
    print("Checking for the latest headlines...")
    api_key = get_news_api_key()
    if not api_key:
        print("NEWS_API_KEY is not set.")
        speak("Please set your News API key before asking for the news.")
        return

    def fetch(endpoint, parameters):
        query = urllib.parse.urlencode(parameters)
        request = urllib.request.Request(
            f"https://newsapi.org/v2/{endpoint}?{query}",
            headers={
                "User-Agent": "JarvisVoiceAssistant/1.0",
                "X-Api-Key": api_key,
            },
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.load(response)

    try:
        print("Fetching news from NewsAPI...")
        data = fetch("top-headlines", {"country": "in", "pageSize": 5})
        if data.get("status") == "ok" and not data.get("articles"):
            print("No India top headlines returned; trying latest India news.")
            data = fetch(
                "everything",
                {"q": "India", "language": "en", "sortBy": "publishedAt", "pageSize": 5},
            )
    except urllib.error.HTTPError as error:
        print(f"News API returned HTTP {error.code}. Check the key and API plan.")
        speak("The news service rejected the request. Please check the API key and plan.")
        return
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        print(f"Could not fetch news: {type(error).__name__}")
        speak("Sorry, I could not fetch the news right now.")
        return

    if data.get("status") != "ok":
        print(f"News API error: {data.get('message', 'Unknown API error')}")
        speak("The news service could not provide headlines.")
        return

    articles = [
        article
        for article in data.get("articles", [])
        if article.get("title")
    ]
    if not articles:
        print("News API returned no articles for either query.")
        speak("There are no headlines available right now.")
        return

    stories = []
    for article in articles[:3]:
        title = article["title"].replace("[Removed]", "").strip()
        details = article.get("description") or article.get("content") or ""
        details = re.sub(r"\s*\[\+\d+ chars\]\s*$", "", details).strip()
        stories.append((title, details[:400]))
        print(f"- {title}")
        if details:
            print(f"  {details}")

    speak_news(stories)


def open_website(command):
    for name, (url, aliases) in WEBSITES.items():
        for word in (name.lower(), *aliases):
            if word in command:
                print(f"Opening {name}...")
                speak(f"Opening {name}.")
                webbrowser.open_new_tab(url)
                return True
    return False


def open_web_destination(command):
    match = re.match(r"^(please )?(open|launch|go to|visit)(?: |$)", command)
    if not match:
        return False

    destination = command[match.end():].strip()
    if not destination:
        speak("Tell me which website to open.")
        return True

    destination = re.sub(r"\s+dot\s+", ".", destination)
    if re.fullmatch(
        r"(?:[a-z0-9-]+ )+(com|org|net|edu|gov|io|ai|co|uk|in|dev|app)",
        destination,
    ):
        destination = destination.replace(" ", ".")

    is_domain = re.fullmatch(
        r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}",
        destination,
    )
    if is_domain:
        url = f"https://{destination}"
        print(f"Opening {destination}...")
        speak(f"Opening {destination}.")
        webbrowser.open_new_tab(url)
    else:
        search_url = (
            "https://www.google.com/search?q="
            + urllib.parse.quote_plus(destination)
        )
        print(f"Searching the web for {destination}...")
        speak(f"Searching the web for {destination}.")
        webbrowser.open_new_tab(search_url)
    return True


def open_app(command):
    command = re.sub(r"^(please )?(open|launch|start)( |$)", "", command).strip()
    for name, (label, program, aliases) in APPS.items():
        if command not in (name, f"the {name}", *aliases):
            continue

        print(f"Opening {label}...")
        if program is None:
            speak(f"Opening {label}.")
            webbrowser.open_new_tab("about:blank")
            return True

        try:
            app_path = program
            if program in ("WINWORD.EXE", "EXCEL.EXE"):
                office_dirs = (
                    Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
                    / "Microsoft Office"
                    / "root"
                    / "Office16",
                    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
                    / "Microsoft Office"
                    / "root"
                    / "Office16",
                )
                app_path = next(
                    (str(folder / program) for folder in office_dirs if (folder / program).is_file()),
                    "",
                )
                if not app_path:
                    print(f"{label} is not installed in a supported Office location.")
                    speak(f"{label} was not found on this computer.")
                    return True

            os.startfile(app_path)
            speak(f"Opening {label}.")
        except OSError as error:
            print(f"Could not open {label}: {error}")
            speak(f"I could not open {label}.")
        return True
    return False


def play_song(command):
    song_name = command.removeprefix("play ").strip()
    for extra in (" song", " music", " track"):
        if song_name.endswith(extra):
            song_name = song_name[:-len(extra)].strip()

    song_name = re.sub(r"\b(by justin bieber|by sia)\b", "", song_name).strip()
    song = musiclibrary.music.get(song_name)
    if not song:
        print(f"Song not found: {song_name}")
        speak(f"I could not find {song_name} in your music library.")
        return

    title, url = song
    print(f"Playing {title}...")
    speak(f"Playing {title}.")
    webbrowser.open_new_tab(url)


def is_news_command(command):
    words = set(command.split())
    asks_for_news = "tell" in words or "what" in words or "headlines" in words
    mentions_news = bool(words.intersection({"news", "nows", "headline", "headlines"}))
    return command in ("news", "nows") or (asks_for_news and mentions_news)


def get_microphone():
    for index in (MICROPHONE_INDEX, 2, 1, 0):
        try:
            return sr.Microphone(device_index=index)
        except OSError:
            pass
    return sr.Microphone()


def handle_command(text):
    command = clean_words(text)
    print(f"You said: {command}")

    if "jarvis" in command:
        speak("yah!!")
        command = command.replace("jarvis", "").strip()

    if is_news_command(command):
        tell_news()
    elif command.startswith("play "):
        play_song(command)
    elif open_app(command):
        return
    elif open_website(command):
        return
    elif open_web_destination(command):
        return
    elif command:
        try:
            answer = ask_ollama(command)
            print(f"Jarvis: {answer}")
            speak(answer)
        except RuntimeError as error:
            print(f"Local AI request failed: {error}")
            speak("I could not get an answer right now. Please check that Ollama is running.")


def main():
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300

    try:
        with get_microphone() as microphone:
            print("Calibrating microphone...")
            recognizer.adjust_for_ambient_noise(microphone, duration=1)
            print("Listening...")
            speak("Jarvis is ready and listening.")

            while True:
                try:
                    audio = recognizer.listen(
                        microphone, timeout=5, phrase_time_limit=10
                    )
                    text = recognizer.recognize_google(audio, language="en-US")
                    handle_command(text)
                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    print("Sorry, I did not catch that.")
                except sr.RequestError as error:
                    print(f"Google speech recognition error: {error}")
    except OSError as error:
        print(f"Microphone error: {error}")


if __name__ == "__main__":
    main()
