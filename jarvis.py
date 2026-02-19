import speech_recognition as sr
from groq import Groq
import pygame
import io
import webbrowser
import os
import subprocess
import requests
from bs4 import BeautifulSoup
import struct
import pyaudio
import pvporcupine
import datetime
import json
from bs4 import BeautifulSoup
from googlesearch import search
import requests
import re
from PIL import ImageGrab
import base64
import io
from gtts import gTTS
import time
import edge_tts
import asyncio

# ==========================================
# BROWSER CONFIGURATION
# ==========================================
# Dynamically find your Windows user folder
USER_PROFILE = os.environ.get('USERPROFILE')
OPERA_GX_PATH = r"C:\Users\mario\AppData\Local\Programs\Opera GX\opera.exe"

# Register Opera GX inside Python's browser list
webbrowser.register('operagx', None, webbrowser.BackgroundBrowser(OPERA_GX_PATH))

# ==========================================
# 1. SETUP & CONFIGURATION
# ==========================================

GROQ_API_KEY = ""
ELEVENLABS_API_KEY = ""
WEATHER_API_KEY = ""
PICOVOICE_API_KEY = ""

TEXT_MODE = False # Set to False when you plug your mic back in!

# Initialize our new Groq brain and ElevenLabs voice
groq_client = Groq(api_key=GROQ_API_KEY)

pygame.mixer.init()

# ==========================================
# 2. NEW ABILITIES (News & Weather)
# ==========================================

def get_weather(city="Thessaloniki"):
    """Fetches the current weather using the OpenWeatherMap API."""
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
    try:
        response = requests.get(url).json()
        if response.get("cod") != "404":
            temp = response["main"]["temp"]
            desc = response["weather"][0]["description"]
            return f"The current temperature in {city} is {temp} degrees Celsius with {desc}."
        return "I couldn't find the weather for that location sir."
    except Exception:
        return "I'm having trouble accessing the weather network sir."

def get_news():
    """Scrapes the top 3 headlines from BBC News."""
    url = 'https://www.bbc.com/news'
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        headlines = soup.find('body').find_all('h3') 
        news_list = [x.text.strip() for x in headlines[:3]] 
        return "Here are the top headlines. " + ". ".join(news_list)
    except Exception:
        return "I am unable to retrieve the news right now sir."

# ==========================================
# 3. CORE FUNCTIONS
# ==========================================

# ==========================================
# "en-GB-RyanNeural" is the closest free voice to JARVIS
# Other options: "en-US-ChristopherNeural", "en-US-GuyNeural"
#
# VOICE SETTINGS
# ==========================================
VOICE = "en-GB-RyanNeural" 

async def generate_voice(text, output_file):
    """Quietly fetches the audio from Microsoft in the background."""
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(output_file)

def speak(text):
    """Plays the audio and syncs the text output perfectly."""
    try:
        output_file = "jarvis_audio.mp3"
        
        # 1. Download the audio quietly in the background FIRST
        asyncio.run(generate_voice(text, output_file))
        
        # 2. Initialize Pygame Mixer and load the downloaded file
        pygame.mixer.init()
        pygame.mixer.music.load(output_file)
        
        # 3. Print the text to the terminal at the EXACT same time we hit play!
        print(f"JARVIS: {text}")
        pygame.mixer.music.play()
        
        # 4. Wait for audio to finish playing
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
            
        # 5. Clean up and delete the file so your drive stays clean
        pygame.mixer.music.stop()
        pygame.mixer.quit()
        if os.path.exists(output_file):
            os.remove(output_file)
            
    except Exception as e:
        print(f"[Voice Error: {e}]")


def listen():
    """Listens to the microphone and converts spoken words into text."""
    recognizer = sr.Recognizer()
    
    with sr.Microphone() as source:
        print("\n[Listening...]")
        # 1. Calibrate for a split second to ignore background room noise
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        
        try:
            # 2. Capture the audio! (timeout=5 means he gives up if you are silent for 5 seconds)
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            print("[Processing...]")
            
            # 3. Use Google's free API to translate the audio to text
            text = recognizer.recognize_google(audio)
            print(f"You: {text}")
            return text.lower()
            
        except sr.WaitTimeoutError:
            # You didn't say anything, just quietly return nothing
            return ""
        except sr.UnknownValueError:
            print("[System: Could not understand the audio.]")
            return ""
        except sr.RequestError as e:
            print(f"[System: Speech API unavailable - {e}]")
            return ""

# 1. Create the memory bank (put this right above your think function)
chat_history = [
    {"role": "system", "content": "You are JARVIS. You speak in a helpful, highly intelligent, and slightly witty tone. Keep your responses very brief—no more than 1 or 2 sentences."}
]
 
MEMORY_FILE = "jarvis_memory.json"

def load_memory():
    """Loads previous conversations from the hard drive."""
    if os.path.exists(MEMORY_FILE):
        try:
            # NEW: Added encoding="utf-8" to force universal character reading
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                memory = json.load(f)
                print(f"\n[System: Successfully restored {len(memory)} memory files.]")
                return memory
        except Exception as e:
            # This will now warn us if the memory fails to load instead of failing silently!
            print(f"\n[Memory Load Error: {e}. Starting fresh.]")
            
    # If no file exists yet, return the default system prompt
    return [
        {"role": "system", "content": "You are JARVIS. You speak in a helpful, highly intelligent, and slightly witty tone. Keep your responses very brief—no more than 1 or 2 sentences."}
    ]

def save_memory(history_list):
    """Saves the current conversation back to the hard drive."""
    # NEW: Added encoding="utf-8" for safe saving
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history_list, f, indent=4)

# 1. Load memory from the hard drive when he boots up!
chat_history = load_memory()

def think(user_input):
    """Sends the ENTIRE chat history to Groq so JARVIS remembers the context."""
    global chat_history
    chat_history.append({"role": "user", "content": user_input})
    
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=chat_history 
        )
        
        reply = response.choices[0].message.content
        chat_history.append({"role": "assistant", "content": reply})
        
        if len(chat_history) > 100:
            chat_history = [chat_history[0]] + chat_history[-99:]
            
        # 2. SAVE the updated memory to the hard drive so it survives a restart!
        save_memory(chat_history)
        
        return reply
        
    except Exception as e:
        print(f"\n[Groq Error: {e}]")
        chat_history.pop() 
        return "I'm sorry, sir. I'm having trouble connecting to my cognitive network."
    


def read_website(url):
    """Fetches a website and extracts only the visible text."""
    try:
        # UPGRADE: Give JARVIS a fully realistic browser disguise
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        # BeautifulSoup parses the raw HTML and extracts only the readable text
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)
        
        # We only return the first 4000 characters so we don't overload his short-term memory!
        return text[:4000] 
    except Exception as e:
        return f"System error reading website: {e}"



def look_at_screen():
    """Captures a screenshot of the main display and sends it to Groq's Vision model."""
    try:
        speak("Accessing display output.")
        
        # 1. Takes a screenshot of your primary monitor
        screenshot = ImageGrab.grab()
        
        # 2. Saves the image into a temporary memory buffer
        buffered = io.BytesIO()
        screenshot.save(buffered, format="JPEG")
        
        # 3. Encode the image into a base64 string
        base64_image = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        speak("Screenshot captured. Processing visual data.")
        
        # 4. Sends the screenshot to Groq's dedicated Vision model!
        response = groq_client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct", 
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "You are JARVIS. Describe what you see on this computer screen in one or two brief, conversational sentences."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ]
        )
        return response.choices[0].message.content
        
    except Exception as e:
        return f"System error processing screen data: {e}"




def execute_command(command):
    """JARVIS's Hands: Intercepts specific commands."""
    cmd = command.lower()
    
    if "open youtube" in cmd:
        speak("Opening YouTube for you sir.")
        # Change to this:
        webbrowser.get('operagx').open("https://www.youtube.com")
        return True
    
    elif "open facebook" in cmd:
        speak("Opening Facebook sir.")
        webbrowser.get('operagx').open("https://www.facebook.com")
        return True
        
    elif "open instagram" in cmd:
        speak("Opening Instagram sir.")
        webbrowser.get('operagx').open("https://www.instagram.com")
        return True
        
    elif "open twitch" in cmd:
        speak("Opening Twitch, sir.")
        webbrowser.get('operagx').open("https://www.twitch.tv")
        return True
        
    elif "open gmail" in cmd or "check my email" in cmd:
        speak("Opening your Gmail inbox sir.")
        # mail.google.com is the direct route to bypass the Google landing page!
        webbrowser.get('operagx').open("https://mail.google.com")
        return True
    
    elif "open spotify" in cmd:
        speak("Opening Spotify sir.")
        # The "start spotify:" command triggers Windows to open the native desktop app
        os.system("start spotify:")
        return True
        
    elif "close spotify" in cmd:
        speak("Shutting down Spotify.")
        # taskkill forcefully terminates the Spotify executable running in the background
        os.system("taskkill /f /im spotify.exe")
        return True
        
    elif "play" in cmd and "on spotify" in cmd:
        # 1. Strip away the trigger words to find the exact song/artist you want
        song = cmd.replace("play ", "").replace("on spotify", "").strip()
        speak(f"Pulling up {song} on Spotify.")
        
        # 2. Format the text so Spotify's search engine understands it (replacing spaces with %20)
        query = song.replace(" ", "%20")
        
        # 3. Force the desktop app to open directly to the search results for that song!
        os.system(f"start spotify:search:{query}")
        return True
    

    elif "open steam" in cmd:
        speak("Opening Steam sir.")
        # The "start steam:" command instantly wakes up the desktop client!
        os.system("start steam:")
        return True
    
    elif "close steam" in cmd:
        speak("Shutting down the Steam client, sir.")
        # The taskkill command forcefully terminates the steam.exe background process
        os.system("taskkill /f /im steam.exe")
        return True
    

    elif "open notepad" in cmd:
        speak("Opening Notepad sir.")
        subprocess.Popen('C:\\Windows\\System32\\notepad.exe') 
        return True
        
    elif "open calculator" in cmd:
        speak("Launching the calculator sir.")
        subprocess.Popen('C:\\Windows\\System32\\calc.exe')
        return True
        
    elif "weather" in cmd:
        speak("Let me check the local sensors sir.")
        weather_report = get_weather()
        speak(weather_report)
        return True
        
    elif "news" in cmd:
        speak("Gathering the latest reports sir.")
        news_report = get_news()
        speak(news_report)
        return True
    
    elif "time" in cmd:
        # 1. Grab the current local time directly from your PC
        now = datetime.datetime.now()
        
        # 2. Format it to be easily spoken (e.g., "07:00 PM")
        current_time = now.strftime("%I:%M %p")
        
        # 3. Have JARVIS speak it out loud
        speak(f"It is currently {current_time} sir.")
        return True
    

    elif "search for" in cmd:
        # 1. Extract exactly what you want to search for
        query = cmd.split("search for")[1].strip()
        speak(f"Searching the global network for {query}.")
        
        try:
            # 2. Get the top URL from Google
            top_url = next(search(query, num_results=1))
            
            # 3. Open it in Opera GX!
            webbrowser.get('operagx').open(top_url)
            
            # 4. Read the text and force JARVIS to summarize it!
            site_text = read_website(top_url)
            prompt = f"I just searched for '{query}'. Summarize this website content briefly: {site_text}"
            
            reply = think(prompt)
            speak(reply)
            return True
        except StopIteration:
            speak("I could not find any search results sir.")
            return True
            
    elif "http" in cmd: 
        # Triggered if you paste a direct link in Text Mode!
        speak("Scanning the provided URL.")
        
        # Find the actual link hidden in your text string
        match = re.search(r'(https?://[^\s]+)', cmd)
        if match:
            url = match.group(1)
            
            # 1. Open the pasted link in Opera GX!
            webbrowser.get('operagx').open(url)
            
            # 2. ACTUALLY READ the website (This is the line that went missing!)
            site_text = read_website(url)
            
            # 3. Summarize the text he just read
            prompt = f"I am sharing a link with you. Read this content and summarize it: {site_text}"
            reply = think(prompt)
            speak(reply)
            return True
        
    elif "look at the screen" in cmd or "what is on my screen" in cmd:
        vision_reply = look_at_screen()
        speak(vision_reply)
        return True    


    return False

# ==========================================
# 4. THE MAIN LOOP
# ==========================================

def main():
    speak("Welcome home sir; I am at your service.")
    
    # ==========================================
    # ROUTE A: TEXT MODE (NO MIC CONNECTED)
    # ==========================================
    if TEXT_MODE:
        print("\n[System Alert: Microphone missing. Wake Word disabled. Falling back to Text Mode.]")
        while True:
            command = listen()
            
            if command.lower() in ["stop", "exit", "quit", "goodbye jarvis", "go to sleep"]:
                speak("Powering down sir.")
                break
                
            if command:
                action_taken = execute_command(command)
                
                if not action_taken:
                    reply = think(command)
                    speak(reply)

    # ==========================================
    # ROUTE B: VOICE MODE (WITH WAKE WORD)
    # ==========================================
    else:
        try:
            porcupine = pvporcupine.create(access_key=PICOVOICE_API_KEY, keywords=["jarvis"])
            pa = pyaudio.PyAudio()
            # If no mic is found, this next line is what causes the OSError!
            audio_stream = pa.open(
                rate=porcupine.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=porcupine.frame_length
            )
            
            print("\n[Background System: Actively listening for 'JARVIS'...]")
            
            while True:
                pcm = audio_stream.read(porcupine.frame_length, exception_on_overflow=False)
                pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
                
                keyword_index = porcupine.process(pcm)
                
                if keyword_index >= 0:
                    print("\n[Wake Word Detected!]")
                    speak("Yes sir?") 
                    
                    command = listen()
                    
                    if command.lower() in ["stop", "exit", "quit"]:
                        speak("Powering down sir")
                        break


                    if "go to sleep" in command or "mute" in command:
                        speak("Standing by sir.")
                        continue

        
                        
                    if command:
                        action_taken = execute_command(command)
                        if not action_taken:
                            reply = think(command)
                            speak(reply)
                    
                    print("\n[Background System: Actively listening for 'JARVIS'...]")
                    
        except Exception as e:
            print(f"\n[Wake Word Error: {e}]")
        finally:
            if 'porcupine' in locals() and porcupine is not None: porcupine.delete()
            if 'audio_stream' in locals() and audio_stream is not None: audio_stream.close()
            if 'pa' in locals() and pa is not None: pa.terminate()

if __name__ == "__main__":
    main()