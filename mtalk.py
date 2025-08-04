#!/usr/bin/env python3
"""
Enhanced Robot Face Expression System with Voice Assistant Integration - FIXED VERSION
Fixes:
1. No color changing while speaking
2. Proper lip sync with vowel detection
3. Local voice detection for wakeup commands
4. Voice-controlled sleep/wake functionality
5. Starts with voice interaction by default
6. Local wake word detection without server dependency
7. Minimum recording time for user input
8. Interactive loading expressions with background color changes
"""

import json
import math
import time
import random
import sys
import os
import threading
import requests
import tempfile
import pyaudio
import wave
import argparse
import logging
import urllib.parse
import struct
import urllib3
import contextlib
import re
import numpy as np
from PIL import Image
from typing import Dict, List, Tuple, Optional, Any
# import speech_recognition as sr
from io import BytesIO
from vosk import Model, KaldiRecognizer
import pyaudio
import json
from robot import handle_input,init_robot,Robot

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    import pygame
    from pygame.locals import *
    from OpenGL.GL import *
    from OpenGL.GLU import *
except ImportError as e:
    print(f"Required libraries not installed: {e}")
    print("Install with: pip install pygame PyOpenGL PyOpenGL_accelerate requests pyaudio pillow numpy SpeechRecognition")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
robot = init_robot("no_movement",logger)
# Global configuration
PARTS_PATH = "parts/"  # Assumes a 'parts' subfolder for images
LIP_EYEBROW_COLOR = (0, 53, 86)  # #003556 in RGB
LIP_EYEBROW_COLOR_GL = (0/255.0, 53/255.0, 86/255.0, 1.0)  # Normalized for OpenGL

# Background colors
BG_COLOR_NORMAL = (0.1, 0.1, 0.8, 1.0)  # Blue background for normal mode
BG_COLOR_LOADING = (0.0, 0.0, 0.0, 1.0)  # Black background for loading mode

# Wake words for local detection
WAKE_WORDS = ['wake', 'wakeup', 'wake up', 'hello', 'start', 'activate', 'robot', 'hey']
SLEEP_WORDS = ['sleep', 'go to sleep', 'goodbye', 'stop', 'bye']

# Enhanced emotion definitions with loading expressions
EMOTIONS = {
    "neutral": {"eyebrow_y": 0.0, "eyebrow_r": 0, "mouth_c": 0.0, "eye_o": 1.0, "pupil_s": 1.0, "eye_steady": False, "eye_move_range": 0.3},
    "happy": {"eyebrow_y": 0.05, "eyebrow_r": -5, "mouth_c": 0.6, "eye_o": 1.0, "pupil_s": 1.0, "eye_steady": False, "eye_move_range": 0.4},
    "sad": {"eyebrow_y": -0.03, "eyebrow_r": 15, "mouth_c": -0.7, "eye_o": 0.6, "pupil_s": 0.9, "eye_steady": False, "eye_move_range": 0.2},
    "angry": {"eyebrow_y": -0.01, "eyebrow_r": -10, "mouth_c": -0.4, "eye_o": 0.9, "pupil_s": 1.0, "eye_steady": False, "eye_move_range": 0.5},
    "surprise": {"eyebrow_y": 0.12, "eyebrow_r": 5, "mouth_c": 0.2, "eye_o": 1.2, "pupil_s": 0.8, "eye_steady": False, "eye_move_range": 0.6},
    "fear": {"eyebrow_y": 0.1, "eyebrow_r": 20, "mouth_c": -0.5, "eye_o": 1.15, "pupil_s": 0.7, "eye_steady": False, "eye_move_range": 0.7},
    "disgust": {"eyebrow_y": -0.02, "eyebrow_r": -5, "mouth_c": -0.6, "eye_o": 0.9, "pupil_s": 1.0, "eye_steady": False, "eye_move_range": 0.3},
    "amusement": {"eyebrow_y": 0.04, "eyebrow_r": -4, "mouth_c": 0.8, "eye_o": 1.0, "pupil_s": 1.0, "eye_steady": False, "eye_move_range": 0.4},
    "frustration": {"eyebrow_y": -0.01, "eyebrow_r": -5, "mouth_c": -0.3, "eye_o": 0.9, "pupil_s": 1.0, "eye_steady": False, "eye_move_range": 0.4},
    "love": {"eyebrow_y": 0.03, "eyebrow_r": -6, "mouth_c": 0.5, "eye_o": 1.0, "pupil_s": 1.2, "eye_steady": False, "eye_move_range": 0.3},
    "embarrassment": {"eyebrow_y": -0.02, "eyebrow_r": 5, "mouth_c": -0.2, "eye_o": 0.8, "pupil_s": 1.1, "eye_steady": False, "eye_move_range": 0.2},
    "confusion": {"eyebrow_y": 0.0, "eyebrow_r": 15, "mouth_c": -0.1, "eye_o": 0.9, "pupil_s": 1.0, "eye_steady": False, "eye_move_range": 0.5},
    "sleepy": {"eyebrow_y": -0.01, "eyebrow_r": 2, "mouth_c": 0.1, "eye_o": 0.2, "pupil_s": 0.1, "eye_steady": True, "eye_move_range": 0.1},
    "talking": {"eyebrow_y": 0.0, "eyebrow_r": 0, "mouth_c": 0.0, "eye_o": 1.0, "pupil_s": 1.0, "eye_steady": False, "eye_move_range": 0.3},
    "cute_neutral": {"eyebrow_y": 0.02, "eyebrow_r": -2, "mouth_c": 0.2, "eye_o": 1.1, "pupil_s": 1.0, "eye_steady": False, "eye_move_range": 0.3},
    
    # Loading expressions - funny and interactive
    "loading_thinking": {"eyebrow_y": 0.08, "eyebrow_r": 10, "mouth_c": -0.2, "eye_o": 0.8, "pupil_s": 0.9, "eye_steady": False, "eye_move_range": 0.8},
    "loading_excited": {"eyebrow_y": 0.1, "eyebrow_r": -8, "mouth_c": 0.4, "eye_o": 1.3, "pupil_s": 1.1, "eye_steady": False, "eye_move_range": 0.9},
    "loading_curious": {"eyebrow_y": 0.06, "eyebrow_r": 12, "mouth_c": 0.1, "eye_o": 1.1, "pupil_s": 0.8, "eye_steady": False, "eye_move_range": 1.0},
    "loading_dizzy": {"eyebrow_y": 0.0, "eyebrow_r": 5, "mouth_c": -0.1, "eye_o": 0.9, "pupil_s": 1.2, "eye_steady": False, "eye_move_range": 1.2},
    "loading_focused": {"eyebrow_y": -0.02, "eyebrow_r": -8, "mouth_c": 0.0, "eye_o": 0.7, "pupil_s": 0.6, "eye_steady": True, "eye_move_range": 0.1},
}

LOADING_EXPRESSIONS = ["loading_thinking", "loading_excited", "loading_curious", "loading_dizzy", "loading_focused"]

class LocalVoiceDetector:
    """Local voice detection for wake commands without server dependency (Offline using Vosk)"""
    
    def __init__(self, model_path="model", rate=16000):
        self.model = Model(model_path)
        self.rate = rate
        self.recognizer = KaldiRecognizer(self.model, self.rate)
        self.audio_interface = pyaudio.PyAudio()
        self.stream = self.audio_interface.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.rate,
            input=True,
            frames_per_buffer=8192
        )
        self.stream.start_stream()
        logger.info("Local voice detector initialized with Vosk")

    def listen_for_wake_word(self, duration=2):
        """Listen for wake words locally using offline Vosk model"""
        try:
            frames = []
            for _ in range(int(self.rate / 4096 * duration)):
                data = self.stream.read(4096, exception_on_overflow=False)
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get("text", "").lower()
                    logger.info(f"Detected speech: {text}")

                    for wake_word in WAKE_WORDS:
                        if wake_word in text:
                            logger.info(f"Wake word detected: {wake_word}")
                            return True
                    
                    for sleep_word in SLEEP_WORDS:
                        if sleep_word in text:
                            logger.info(f"Sleep word detected: {sleep_word}")
                            return False

        except Exception as e:
            logger.error(f"Voice detection error: {e}")
        
        return None

class VoiceAssistantClient:
    """Voice Assistant Client for API Communication - Enhanced"""
    
    def __init__(self, api_url="https://aiec.guni.ac.in:8111", user_name="test_user", verify_ssl=False):
        self.api_url = api_url
        self.user_name = user_name
        self.verify_ssl = verify_ssl
        
        # Audio Configuration with minimum recording time
        self.audio_config = {
            'chunk': 1024,
            'format': pyaudio.paInt16,
            'channels': 1,
            'rate': 16000,
            'record_seconds': 8,  # Increased minimum time
            'min_record_seconds': 3  # Minimum recording time
        }
        
        # State tracking
        self.is_recording = False
        self.is_processing = False
        self.is_speaking = False
        self.api_status = "Disconnected"
        self.last_user_input = ""
        self.last_ai_response = ""
        
        # Test connection
        self.test_api_connection()
    
    def test_api_connection(self):
        """Test connection to the voice assistant API"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5, verify=self.verify_ssl)
            if response.status_code == 200:
                self.api_status = "Connected"
                logger.info("API connection successful")
            else:
                self.api_status = f"Error {response.status_code}"
                logger.warning(f"API responded with status: {response.status_code}")
        except requests.exceptions.SSLError as e:
            self.api_status = "SSL Certificate Error"
            logger.error(f"SSL Certificate error connecting to API: {e}")
        except requests.exceptions.RequestException as e:
            self.api_status = "Connection Error"
            logger.error(f"Cannot connect to API at {self.api_url}: {e}")
    
    def record_audio_with_minimum_time(self, min_seconds=None):
        """Record audio with minimum time guarantee"""
        min_seconds = min_seconds or self.audio_config['min_record_seconds']
        max_seconds = self.audio_config['record_seconds']
        
        try:
            audio = pyaudio.PyAudio()
            temp_audio_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            temp_audio_path = temp_audio_file.name
            temp_audio_file.close()
            
            stream = audio.open(
                format=self.audio_config['format'],
                channels=self.audio_config['channels'],
                rate=self.audio_config['rate'],
                input=True,
                frames_per_buffer=self.audio_config['chunk']
            )
            
            logger.info(f"Recording started... (min: {min_seconds}s, max: {max_seconds}s)")
            frames = []
            
            frames_per_second = self.audio_config['rate'] / self.audio_config['chunk']
            min_frames = int(frames_per_second * min_seconds)
            max_frames = int(frames_per_second * max_seconds)
            
            for i in range(max_frames):
                if not self.is_recording and i >= min_frames:
                    break
                data = stream.read(self.audio_config['chunk'], exception_on_overflow=False)
                frames.append(data)
            
            stream.stop_stream()
            stream.close()
            audio.terminate()
            
            actual_duration = len(frames) / frames_per_second
            logger.info(f"Recording finished. Duration: {actual_duration:.1f}s")
            
            wf = wave.open(temp_audio_path, 'wb')
            wf.setnchannels(self.audio_config['channels'])
            wf.setsampwidth(audio.get_sample_size(self.audio_config['format']))
            wf.setframerate(self.audio_config['rate'])
            wf.writeframes(b''.join(frames))
            wf.close()
            
            return temp_audio_path
            
        except Exception as e:
            logger.error(f"Audio recording error: {e}")
            return None
    
    def send_audio_to_api(self, audio_path):
        """Send audio to the API and get response"""
        try:
            logger.info(f"Sending audio to API: {self.api_url}")
            
            with open(audio_path, 'rb') as audio_file:
                files = {'audio': ('audio.wav', audio_file, 'audio/wav')}
                data = {'user_name': self.user_name}
                
                response = requests.post(
                    f"{self.api_url}/process_audio",
                    files=files,
                    data=data,
                    timeout=30,
                    verify=self.verify_ssl
                )
            
            # Cleanup temp file
            try:
                os.unlink(audio_path)
            except:
                pass
            
            if response.status_code == 200:
                robot_expression = response.headers.get('X-Robot-Expression', 'cute_neutral')
                encoded_text_response = response.headers.get('X-LLM-Text', 'I am here to help!')
                language_used = response.headers.get('X-Language-Used', 'english')
                audio_format = response.headers.get('X-Audio-Format', 'mp3')
                robot_action_response = response.headers.get('X-Robot-Action', 'none')
                
                try:
                    text_response = urllib.parse.unquote(encoded_text_response)
                except Exception:
                    text_response = encoded_text_response
                
                file_extension = '.wav' if audio_format == 'wav' else '.mp3'
                temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
                temp_audio.write(response.content)
                temp_audio.close()
                handle_input(robot, logger, robot_action_response)
                result = {
                    'robot_expression': robot_expression,
                    'text_response': text_response,
                    'language_used': language_used,
                    'audio_file': temp_audio.name,
                    'audio_format': audio_format,
                    'user_input': f"Processed via {self.user_name}"
                }
                
                logger.info(f"API Response parsed: {result}")
                return result
            else:
                logger.error(f"API Error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"API communication error: {e}")
            return None
    
    def play_audio_response(self, response_data, avatar_state):
        """Play audio response from API with improved lip sync"""
        if not response_data or 'audio_file' not in response_data:
            return
        
        try:
            audio_file_path = response_data['audio_file']
            audio_format = response_data.get('audio_format', 'mp3')
            text = response_data.get('text_response', '')
            
            logger.info(f"Playing {audio_format} audio file: {audio_file_path}")
            
            # Initialize pygame mixer
            try:
                pygame.mixer.quit()
            except:
                pass
            
            if audio_format == 'wav':
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=1024)
            else:
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            
            # Set up enhanced lip sync
            avatar_state.is_speaking = True
            avatar_state.speech_start_time = time.time()
            avatar_state.speech_text = text
            avatar_state.speech_phonemes = self.text_to_enhanced_phonemes(text)
            avatar_state.current_phoneme_index = 0
            
            try:
                pygame.mixer.music.load(audio_file_path)
                pygame.mixer.music.play()
                
                # Wait for playback to complete
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                    if not self.is_speaking:
                        pygame.mixer.music.stop()
                        break
                
                logger.info("Audio playback completed")
            except pygame.error as e:
                logger.error(f"Pygame audio error: {e}")
            
            # Reset speaking state
            avatar_state.is_speaking = False
            avatar_state.mouth_open_ratio = 0.0
            avatar_state.upper_lip_y = 0.0
            avatar_state.lower_lip_y = 0.0
            
            # Cleanup temp file
            try:
                os.unlink(audio_file_path)
            except:
                pass
                
        except Exception as e:
            logger.error(f"Audio playback error: {e}")
    
    def text_to_enhanced_phonemes(self, text):
        """Enhanced phoneme detection with better vowel recognition"""
        phonemes = []
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Vowel patterns for better lip sync
        vowel_patterns = {
            'a': ('vowel_wide_a', 0.20),      # Wide open mouth
            'e': ('vowel_mid_e', 0.18),       # Medium open, slightly wide
            'i': ('vowel_narrow_i', 0.16),    # Narrow, high tongue
            'o': ('vowel_round_o', 0.18),     # Round lips, medium open
            'u': ('vowel_round_u', 0.16),     # Round lips, smaller opening
            'ay': ('vowel_wide_a', 0.18),     # Diphthong
            'ow': ('vowel_round_o', 0.18),    # Diphthong
        }
        
        consonant_patterns = {
            'b': ('bilabial_b', 0.12),        # Lips together
            'p': ('bilabial_p', 0.12),        # Lips together
            'm': ('bilabial_m', 0.14),        # Lips together, longer
            'f': ('labiodental_f', 0.12),     # Teeth on lip
            'v': ('labiodental_v', 0.12),     # Teeth on lip
            't': ('dental_t', 0.10),          # Tongue to teeth
            'd': ('dental_d', 0.10),          # Tongue to teeth
            'n': ('dental_n', 0.12),          # Tongue to teeth, longer
            'l': ('dental_l', 0.12),          # Tongue to teeth
            'r': ('dental_r', 0.14),          # Tongue movement
            's': ('sibilant_s', 0.14),        # Hissing sound
            'z': ('sibilant_z', 0.14),        # Hissing sound
            'sh': ('sibilant_sh', 0.16),      # Wider hissing
            'ch': ('sibilant_ch', 0.14),      # Sharp hissing
            'k': ('velar_k', 0.08),           # Back of tongue
            'g': ('velar_g', 0.08),           # Back of tongue
            'w': ('rounded_w', 0.12),         # Rounded lips
            'y': ('palatal_y', 0.10),         # High tongue
        }
        
        for word in words:
            # Process each character with context
            i = 0
            while i < len(word):
                char = word[i]
                
                # Check for common digraphs first
                if i < len(word) - 1:
                    digraph = word[i:i+2]
                    if digraph in consonant_patterns:
                        phonemes.append(consonant_patterns[digraph])
                        i += 2
                        continue
                    elif digraph in vowel_patterns:
                        phonemes.append(vowel_patterns[digraph])
                        i += 2
                        continue
                
                # Single character processing
                if char in vowel_patterns:
                    phonemes.append(vowel_patterns[char])
                elif char in consonant_patterns:
                    phonemes.append(consonant_patterns[char])
                else:
                    # Default consonant
                    phonemes.append(('consonant_default', 0.08))
                
                i += 1
            
            # Add word boundary
            phonemes.append(('pause', 0.05))
        
        return phonemes
    
    def store_conversation(self, user_input, ai_response, language_used='english'):
        """Store conversation in the server database"""
        try:
            if not user_input or not ai_response:
                logger.warning("Skipping conversation storage - missing input or response")
                return False
            
            data = {
                'user_name': self.user_name,
                'user_input': user_input,
                'ai_response': ai_response,
                'language_used': language_used
            }
            
            response = requests.post(
                f"{self.api_url}/conversation",
                data=data,
                timeout=10,
                verify=self.verify_ssl
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'added':
                    logger.info("Conversation stored successfully")
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Error storing conversation: {e}")
            return False

class AvatarState:
    """Enhanced Avatar State with loading mode support"""
    def __init__(self):
        # Emotion system
        self.target_emotion = "sleepy"  # Start in sleep mode
        self.current_emotion = "sleepy"
        self.emotion_transition_speed = 3.0
        
        # Loading mode
        self.is_loading = False
        self.loading_start_time = 0
        self.loading_expression_index = 0
        self.next_loading_change = 0
        
        # Eye system
        self.eye_open_ratio = 1.0
        self.target_eye_open_ratio = 1.0
        self.is_blinking = False
        self.blink_start_time = 0
        self.blink_duration = 0.12
        self.next_blink_time = time.time() + 3
        
        # Eyebrow system
        self.eyebrow_y, self.target_eyebrow_y = 0.0, 0.0
        self.eyebrow_r, self.target_eyebrow_r = 0.0, 0.0
        
        # Pupil system
        self.pupil_pos = np.array([0.0, 0.0])
        self.target_pupil_pos = np.array([0.0, 0.0])
        self.next_gaze_shift_time = time.time() + 2
        self.pupil_size, self.target_pupil_size = 1.0, 1.0
        
        # Mouth system
        self.mouth_open_ratio = 0.0
        self.mouth_curve, self.target_mouth_curve = 0.0, 0.0
        self.upper_lip_y = 0.0
        self.lower_lip_y = 0.0
        
        # Speech system
        self.is_speaking = False
        self.speech_start_time = 0
        self.speech_text = ""
        self.speech_phonemes = []
        self.current_phoneme_index = 0
        
        # Eye movement
        self.eye_movement_enabled = True
        self.eye_movement_range = 0.3
        
        # Sleep and special states
        self.sleep_animation_phase = 0.0
        self.is_sleeping = True  # Start sleeping
        self.breathing_offset = 0.0
        
        # Mouth width tracking
        self.current_mouth_width = 0.0
        self.target_mouth_width = 0.0

class TextureManager:
    """Manages all texture loading and handling"""
    
    def __init__(self, parts_path=PARTS_PATH):
        self.parts_path = parts_path
        self.textures = {}
        self.texture_info = {}
        self.load_all_textures()
    
    def load_texture(self, image_path):
        """Load a single texture"""
        if not os.path.exists(image_path):
            logger.error(f"Texture not found: {image_path}")
            # Create a placeholder texture
            return self.create_placeholder_texture(), 64, 64
        
        try:
            img = Image.open(image_path).convert("RGBA")
            img_data = np.array(list(img.getdata()), np.uint8)
            texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, img.width, img.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
            return texture_id, img.width, img.height
        except Exception as e:
            logger.error(f"Error loading texture '{image_path}': {e}")
            return self.create_placeholder_texture(), 64, 64
    
    def create_placeholder_texture(self):
        """Create a placeholder texture when image files are missing"""
        # Create a simple 64x64 white texture
        img_data = np.full((64, 64, 4), 255, dtype=np.uint8)
        texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 64, 64, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
        return texture_id
    
    def load_all_textures(self):
        """Load all required textures"""
        logger.info("Loading textures...")
        
        # Try to load textures, fall back to placeholder if missing
        texture_files = {
            "base": "base.png",
            "l_eye_bg": "left_eye_background_and_border.png",
            "r_eye_bg": "right_eye_background_and_border.png",
            "l_pupil": "left_eye_pupil.png",
            "r_pupil": "right_eye_pupil.png",
        }
        
        for key, filename in texture_files.items():
            file_path = os.path.join(self.parts_path, filename)
            tex_id, w, h = self.load_texture(file_path)
            self.textures[key] = tex_id
            self.texture_info[key] = (w, h)
        
        logger.info(f"Loaded {len(self.textures)} textures")

class FaceRenderer:
    """Enhanced Face Renderer with loading mode support"""
    
    def __init__(self, window_width, window_height, texture_manager):
        self.window_width = window_width
        self.window_height = window_height
        self.texture_manager = texture_manager
        self.update_face_dimensions()
        
        # Animation timing
        self.last_update_time = time.time()
        
        # Background color state
        self.current_bg_color = list(BG_COLOR_NORMAL)
        self.target_bg_color = list(BG_COLOR_NORMAL)
    
    def update_face_dimensions(self):
        """Update face dimensions based on window size"""
        self.center_x = self.window_width / 2
        self.center_y = self.window_height / 2
        
        # Scale face based on window size
        base_size = min(self.window_width, self.window_height)
        self.face_height = base_size * 0.8
        
        # Get aspect ratio from base texture if available
        if "base" in self.texture_manager.texture_info:
            base_w, base_h = self.texture_manager.texture_info["base"]
            aspect_ratio = base_w / base_h
            self.face_width = self.face_height * aspect_ratio
        else:
            self.face_width = self.face_height * 0.8
        
        # Calculate component dimensions relative to face size
        self.eye_y_offset = self.face_height * 0.08
        self.eye_x_offset = self.face_width * 0.18
        self.eye_size = self.face_width * 0.28
        self.pupil_size = self.eye_size * 0.6
        
        # Eyebrow dimensions
        self.brow_y_offset = self.face_height * 0.22
        self.brow_size = self.eye_size * 1.0
        
        # Mouth dimensions
        self.mouth_y_offset = self.face_height * 0.2
        self.mouth_width = self.face_width * 0.25
        self.mouth_height = self.face_width * 0.06
        
        logger.info(f"Face dimensions updated: {self.face_width}x{self.face_height}")
    
    def resize_window(self, new_width, new_height):
        """Handle window resize"""
        self.window_width = new_width
        self.window_height = new_height
        self.update_face_dimensions()
        
        # Update OpenGL viewport
        glViewport(0, 0, new_width, new_height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluOrtho2D(0, new_width, 0, new_height)
        glMatrixMode(GL_MODELVIEW)
    
    def update_background_color(self, is_loading, dt):
        """Update background color based on mode"""
        if is_loading:
            self.target_bg_color = list(BG_COLOR_LOADING)
        else:
            self.target_bg_color = list(BG_COLOR_NORMAL)
        
        # Smooth transition
        for i in range(4):
            self.current_bg_color[i] += (self.target_bg_color[i] - self.current_bg_color[i]) * dt * 3.0
        
        glClearColor(*self.current_bg_color)
    
    def create_quad_mesh(self, cx, cy, width, height):
        """Create a quad mesh for rendering"""
        x1, y1 = cx - width / 2, cy - height / 2
        x2, y2 = cx + width / 2, cy + height / 2
        vertices = np.array([(x1, y1), (x2, y1), (x2, y2), (x1, y2)], dtype=np.float32)
        tex_coords = np.array([(0, 1), (1, 1), (1, 0), (0, 0)], dtype=np.float32)
        return vertices, tex_coords
    
    def create_curved_eyebrow_mesh(self, cx, cy, width, height, curve_strength=0.3):
        """Create curved eyebrow mesh"""
        segments = 10
        vertices = []
        
        for i in range(segments + 1):
            t = i / segments
            x = cx - width/2 + t * width
            curve_y = math.sin(t * math.pi) * curve_strength * height
            top_y = cy + height/2 + curve_y
            bottom_y = cy - height/2 + curve_y * 0.3
            vertices.extend([(x, bottom_y), (x, top_y)])
        
        return np.array(vertices, dtype=np.float32)
    
    def create_enhanced_lip_mesh(self, cx, cy, width, height, phoneme_type, is_upper=True, curve_amount=0.0, segments=32):
        """Create enhanced lip mesh based on phoneme type for realistic speech"""
        def cubic_bezier(p0, p1, p2, p3, t):
            u = 1 - t
            return (u**3)*p0 + 3*(u**2)*t*p1 + 3*u*(t**2)*p2 + (t**3)*p3
        
        # Phoneme-specific lip shapes
        if phoneme_type.startswith('vowel_wide'):
            # Wide open mouth (a, e)
            if is_upper:
                p0 = np.array([0.0, 0.1])
                p1 = np.array([0.25, 0.4 + curve_amount])
                p2 = np.array([0.75, 0.4 + curve_amount])
                p3 = np.array([1.0, 0.1])
            else:
                p0 = np.array([0.0, -0.1 - curve_amount])
                p1 = np.array([0.25, -0.5 - curve_amount])
                p2 = np.array([0.75, -0.5 - curve_amount])
                p3 = np.array([1.0, -0.1 - curve_amount])
        
        elif phoneme_type.startswith('vowel_round'):
            # Round lips (o, u)
            if is_upper:
                p0 = np.array([0.0, 0.05])
                p1 = np.array([0.25, 0.25 + curve_amount])
                p2 = np.array([0.75, 0.25 + curve_amount])
                p3 = np.array([1.0, 0.05])
            else:
                p0 = np.array([0.0, -0.05 - curve_amount])
                p1 = np.array([0.25, -0.25 - curve_amount])
                p2 = np.array([0.75, -0.25 - curve_amount])
                p3 = np.array([1.0, -0.05 - curve_amount])
        
        elif phoneme_type.startswith('vowel_narrow'):
            # Narrow opening (i)
            if is_upper:
                p0 = np.array([0.0, 0.02])
                p1 = np.array([0.25, 0.15 + curve_amount])
                p2 = np.array([0.75, 0.15 + curve_amount])
                p3 = np.array([1.0, 0.02])
            else:
                p0 = np.array([0.0, -0.02 - curve_amount])
                p1 = np.array([0.25, -0.15 - curve_amount])
                p2 = np.array([0.75, -0.15 - curve_amount])
                p3 = np.array([1.0, -0.02 - curve_amount])
        
        elif phoneme_type.startswith('bilabial'):
            # Lips together (b, p, m)
            if is_upper:
                p0 = np.array([0.0, 0.0])
                p1 = np.array([0.25, 0.05 + curve_amount])
                p2 = np.array([0.75, 0.05 + curve_amount])
                p3 = np.array([1.0, 0.0])
            else:
                p0 = np.array([0.0, 0.0 - curve_amount])
                p1 = np.array([0.25, -0.05 - curve_amount])
                p2 = np.array([0.75, -0.05 - curve_amount])
                p3 = np.array([1.0, 0.0 - curve_amount])
        
        else:
            # Default shape
            if is_upper:
                p0 = np.array([0.0, 0.0])
                p1 = np.array([0.25, 0.2 + curve_amount])
                p2 = np.array([0.75, 0.2 + curve_amount])
                p3 = np.array([1.0, 0.0])
            else:
                p0 = np.array([0.0, 0.1 - curve_amount])
                p1 = np.array([0.25, -0.2 - curve_amount])
                p2 = np.array([0.75, -0.2 - curve_amount])
                p3 = np.array([1.0, 0.1 - curve_amount])
        
        # Generate mesh
        thickness = 0.5
        outer, inner = [], []
        for i in range(segments + 1):
            t = i / segments
            x_norm, y_norm = cubic_bezier(p0, p1, p2, p3, t)
            x_world = cx - width/2 + x_norm * width
            y_world = cy + y_norm * height
            
            dir_y = 1.0 if is_upper else -1.0
            offset = dir_y * thickness * height
            outer.append((x_world, y_world))
            inner.append((x_world, y_world - offset))
        
        verts = []
        for (xo, yo), (xi, yi) in zip(outer, inner):
            verts.extend([(xo, yo), (xi, yi)])
        return np.array(verts, dtype=np.float32)
    
    def draw_quad(self, vertices, tex_coords, texture_id):
        """Draw textured quad"""
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        glVertexPointer(2, GL_FLOAT, 0, vertices)
        glTexCoordPointer(2, GL_FLOAT, 0, tex_coords)
        glDrawArrays(GL_QUADS, 0, 4)
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        glDisable(GL_TEXTURE_2D)
    
    def draw_curved_shape(self, vertices, color):
        """Draw curved shape using triangle strip - FIXED: No color change during speech"""
        glDisable(GL_TEXTURE_2D)
        # Always use the same color, don't change during speech
        glColor4f(*color)
        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointer(2, GL_FLOAT, 0, vertices)
        glDrawArrays(GL_TRIANGLE_STRIP, 0, len(vertices))
        glDisableClientState(GL_VERTEX_ARRAY)
        glColor4f(1.0, 1.0, 1.0, 1.0)  # Reset to white
    
    def draw_scaled_quad(self, vertices, tex_coords, texture_id, scale_x=1.0, scale_y=1.0):
        """Draw scaled quad"""
        glPushMatrix()
        center_x = (vertices[0][0] + vertices[2][0]) / 2
        center_y = (vertices[0][1] + vertices[2][1]) / 2
        glTranslatef(center_x, center_y, 0)
        glScalef(scale_x, scale_y, 1.0)
        glTranslatef(-center_x, -center_y, 0)
        self.draw_quad(vertices, tex_coords, texture_id)
        glPopMatrix()
    
    def draw_cropped_quad(self, vertices, tex_coords, texture_id, crop_top=0.0, crop_bottom=0.0):
        """Draw cropped quad for sleep animation"""
        glPushMatrix()
        cropped_vertices = np.copy(vertices)
        cropped_tex_coords = np.copy(tex_coords)
        
        height = vertices[2][1] - vertices[0][1]
        
        if crop_top > 0:
            crop_pixels = height * crop_top
            cropped_vertices[2][1] -= crop_pixels
            cropped_vertices[3][1] -= crop_pixels
            cropped_tex_coords[2][1] = crop_top
            cropped_tex_coords[3][1] = crop_top
        
        if crop_bottom > 0:
            crop_pixels = height * crop_bottom
            cropped_vertices[0][1] += crop_pixels
            cropped_vertices[1][1] += crop_pixels
            cropped_tex_coords[0][1] = 1.0 - crop_bottom
            cropped_tex_coords[1][1] = 1.0 - crop_bottom
        
        self.draw_quad(cropped_vertices, cropped_tex_coords, texture_id)
        glPopMatrix()
    
    def create_dynamic_coordinated_mouth_mesh(self, cx, cy, base_width, base_height, phoneme_type, curve_amount=0.0, emotion_name="neutral", segments=32):
        """Create coordinated lips with dynamic width/length based on phonemes and emotions"""
        
        def cubic_bezier(p0, p1, p2, p3, t):
            u = 1 - t
            return (u**3)*p0 + 3*(u**2)*t*p1 + 3*u*(t**2)*p2 + (t**3)*p3
        
        # Emotion-based mouth width multipliers
        emotion_width_factors = {
            'happy': 1.4,          # Much wider smile
            'amusement': 1.5,      # Even wider for laughter
            'love': 1.2,           # Gentle wider smile
            'surprise': 1.3,       # Wide open in surprise
            'fear': 0.8,           # Tighter, smaller mouth
            'sad': 0.7,            # Narrow, downturned
            'angry': 0.9,          # Tense, slightly narrow
            'disgust': 0.8,        # Tight, disgusted expression
            'embarrassment': 0.8,  # Shy, smaller mouth
            'confusion': 0.9,      # Slightly uncertain
            'frustration': 0.85,   # Tense
            'sleepy': 0.6,         # Very small, relaxed
            'talking': 1.0,        # Normal when just talking
            'cute_neutral': 1.1,   # Slightly wider for cuteness
            'neutral': 1.0,        # Baseline
            # Loading expressions
            'loading_thinking': 0.9,
            'loading_excited': 1.3,
            'loading_curious': 1.1,
            'loading_dizzy': 0.8,
            'loading_focused': 0.8,
        }
        
        # Phoneme-based width adjustments (additional to emotion)
        phoneme_width_factors = {
            'vowel_wide_a': 1.3,   # "Ah" - wide mouth
            'vowel_mid_e': 1.2,    # "Eh" - moderately wide
            'vowel_narrow_i': 0.7, # "Ee" - narrow, pulled back
            'vowel_round_o': 0.9,  # "Oh" - round but not wide
            'vowel_round_u': 0.8,  # "Oo" - narrow and round
            'bilabial_b': 1.0,     # Normal width for "B"
            'bilabial_p': 1.0,     # Normal width for "P"
            'bilabial_m': 1.0,     # Normal width for "M"
            'labiodental_f': 0.9,  # Slightly narrow for "F"
            'labiodental_v': 0.9,  # Slightly narrow for "V"
            'dental_t': 1.0,       # Normal for "T"
            'dental_d': 1.0,       # Normal for "D"
            'dental_n': 1.0,       # Normal for "N"
            'dental_l': 1.0,       # Normal for "L"
            'dental_r': 1.0,       # Normal for "R"
            'sibilant_s': 0.85,    # Narrow for "S"
            'sibilant_z': 0.85,    # Narrow for "Z"
            'sibilant_sh': 0.9,    # Slightly narrow for "SH"
            'sibilant_ch': 0.9,    # Slightly narrow for "CH"
            'velar_k': 1.0,        # Normal for "K"
            'velar_g': 1.0,        # Normal for "G"
            'rounded_w': 0.8,      # Narrow and round for "W"
            'palatal_y': 0.9,      # Slightly narrow for "Y"
            'consonant_default': 1.0,
            'pause': 1.0,
            'neutral': 1.0
        }
        
        # Calculate dynamic width
        emotion_factor = emotion_width_factors.get(emotion_name, 1.0)
        phoneme_factor = phoneme_width_factors.get(phoneme_type, 1.0)
        
        # Combine factors - emotion provides base, phoneme modifies it
        total_width_factor = emotion_factor * phoneme_factor
        dynamic_width = base_width * total_width_factor
        
        # Ensure width doesn't go too extreme
        dynamic_width = max(base_width * 0.4, min(base_width * 1.8, dynamic_width))
        
        # Define mouth opening parameters based on phonemes
        mouth_configs = {
            'vowel_wide_a': {
                'opening_width': 0.8, 'opening_height': 0.8,
                'upper_curve': 0.3, 'lower_curve': 0.5,
                'lip_thickness': 0.15, 'roundness': 0.2
            },
            'vowel_mid_e': {
                'opening_width': 0.7, 'opening_height': 0.6,
                'upper_curve': 0.25, 'lower_curve': 0.35,
                'lip_thickness': 0.12, 'roundness': 0.3
            },
            'vowel_narrow_i': {
                'opening_width': 0.3, 'opening_height': 0.25,
                'upper_curve': 0.1, 'lower_curve': 0.15,
                'lip_thickness': 0.1, 'roundness': 0.1
            },
            'vowel_round_o': {
                'opening_width': 0.5, 'opening_height': 0.7,
                'upper_curve': 0.4, 'lower_curve': 0.4,
                'lip_thickness': 0.18, 'roundness': 0.9
            },
            'vowel_round_u': {
                'opening_width': 0.3, 'opening_height': 0.5,
                'upper_curve': 0.3, 'lower_curve': 0.3,
                'lip_thickness': 0.16, 'roundness': 0.95
            },
            'bilabial_b': {
                'opening_width': 0.0, 'opening_height': 0.0,
                'upper_curve': 0.05, 'lower_curve': 0.05,
                'lip_thickness': 0.12, 'roundness': 0.2
            },
            'bilabial_p': {
                'opening_width': 0.0, 'opening_height': 0.0,
                'upper_curve': 0.05, 'lower_curve': 0.05,
                'lip_thickness': 0.12, 'roundness': 0.2
            },
            'bilabial_m': {
                'opening_width': 0.0, 'opening_height': 0.0,
                'upper_curve': 0.08, 'lower_curve': 0.08,
                'lip_thickness': 0.14, 'roundness': 0.3
            },
            'labiodental_f': {
                'opening_width': 0.2, 'opening_height': 0.15,
                'upper_curve': 0.1, 'lower_curve': 0.2,
                'lip_thickness': 0.1, 'roundness': 0.1
            },
            'labiodental_v': {
                'opening_width': 0.2, 'opening_height': 0.15,
                'upper_curve': 0.1, 'lower_curve': 0.2,
                'lip_thickness': 0.1, 'roundness': 0.1
            },
            'dental_t': {
                'opening_width': 0.3, 'opening_height': 0.25,
                'upper_curve': 0.15, 'lower_curve': 0.2,
                'lip_thickness': 0.1, 'roundness': 0.2
            },
            'dental_d': {
                'opening_width': 0.3, 'opening_height': 0.25,
                'upper_curve': 0.15, 'lower_curve': 0.2,
                'lip_thickness': 0.1, 'roundness': 0.2
            },
            'dental_n': {
                'opening_width': 0.25, 'opening_height': 0.2,
                'upper_curve': 0.12, 'lower_curve': 0.18,
                'lip_thickness': 0.12, 'roundness': 0.2
            },
            'dental_l': {
                'opening_width': 0.3, 'opening_height': 0.2,
                'upper_curve': 0.12, 'lower_curve': 0.18,
                'lip_thickness': 0.1, 'roundness': 0.2
            },
            'dental_r': {
                'opening_width': 0.35, 'opening_height': 0.25,
                'upper_curve': 0.15, 'lower_curve': 0.2,
                'lip_thickness': 0.12, 'roundness': 0.25
            },
            'sibilant_s': {
                'opening_width': 0.15, 'opening_height': 0.1,
                'upper_curve': 0.08, 'lower_curve': 0.12,
                'lip_thickness': 0.08, 'roundness': 0.1
            },
            'sibilant_z': {
                'opening_width': 0.15, 'opening_height': 0.1,
                'upper_curve': 0.08, 'lower_curve': 0.12,
                'lip_thickness': 0.08, 'roundness': 0.1
            },
            'sibilant_sh': {
                'opening_width': 0.2, 'opening_height': 0.15,
                'upper_curve': 0.1, 'lower_curve': 0.15,
                'lip_thickness': 0.1, 'roundness': 0.3
            },
            'sibilant_ch': {
                'opening_width': 0.18, 'opening_height': 0.12,
                'upper_curve': 0.08, 'lower_curve': 0.12,
                'lip_thickness': 0.09, 'roundness': 0.2
            },
            'velar_k': {
                'opening_width': 0.25, 'opening_height': 0.2,
                'upper_curve': 0.1, 'lower_curve': 0.15,
                'lip_thickness': 0.1, 'roundness': 0.2
            },
            'velar_g': {
                'opening_width': 0.25, 'opening_height': 0.2,
                'upper_curve': 0.1, 'lower_curve': 0.15,
                'lip_thickness': 0.1, 'roundness': 0.2
            },
            'rounded_w': {
                'opening_width': 0.2, 'opening_height': 0.3,
                'upper_curve': 0.2, 'lower_curve': 0.2,
                'lip_thickness': 0.14, 'roundness': 0.8
            },
            'palatal_y': {
                'opening_width': 0.2, 'opening_height': 0.15,
                'upper_curve': 0.1, 'lower_curve': 0.15,
                'lip_thickness': 0.1, 'roundness': 0.3
            },
            'consonant_default': {
                'opening_width': 0.2, 'opening_height': 0.15,
                'upper_curve': 0.1, 'lower_curve': 0.15,
                'lip_thickness': 0.1, 'roundness': 0.2
            },
            'pause': {
                'opening_width': 0.05, 'opening_height': 0.03,
                'upper_curve': 0.05, 'lower_curve': 0.08,
                'lip_thickness': 0.1, 'roundness': 0.2
            },
            'neutral': {
                'opening_width': 0.1, 'opening_height': 0.05,
                'upper_curve': 0.05, 'lower_curve': 0.08,
                'lip_thickness': 0.1, 'roundness': 0.2
            }
        }
        
        # Get configuration for current phoneme
        config = mouth_configs.get(phoneme_type, mouth_configs['neutral'])
        
        # Calculate actual dimensions
        actual_width = dynamic_width
        actual_height = base_height
        
        opening_width = config['opening_width'] * actual_width
        opening_height = config['opening_height'] * actual_height
        lip_thickness = config['lip_thickness'] * actual_height
        roundness = config['roundness']
        
        # Adjust curves based on emotion curve_amount
        upper_curve_strength = config['upper_curve'] + curve_amount * 0.4
        lower_curve_strength = config['lower_curve'] - curve_amount * 0.4
        
        # Additional emotion-based curve adjustments
        if emotion_name in ['happy', 'amusement', 'love']:
            upper_curve_strength *= 0.8  # Less upper curve for smiles
            lower_curve_strength *= 1.3  # More lower curve for smiles
        elif emotion_name in ['sad', 'frustration']:
            upper_curve_strength *= 1.2  # More upper curve for frowns
            lower_curve_strength *= 0.7  # Less lower curve for frowns
        
        vertices = []
        
        # Create mouth opening and lip contours with dynamic width
        for i in range(segments + 1):
            t = i / segments
            
            # X position along the DYNAMIC mouth width
            x = cx - actual_width/2 + t * actual_width
            
            # Calculate opening shape based on roundness
            if roundness > 0.6:  # Round shapes (o, u, w)
                # Elliptical opening with proper roundness
                angle = t * math.pi
                opening_y_offset = math.sin(angle) * opening_height/2
                
                # Create proper circular/oval shape
                distance_from_center = abs(t - 0.5) * 2  # 0 at center, 1 at edges
                opening_x_factor = math.sqrt(1 - distance_from_center ** (2.5 - roundness))
                opening_y_offset *= opening_x_factor
                
            elif phoneme_type.startswith('vowel_wide'):  # Wide shapes (a, e)
                # Wide opening across most of the mouth
                center_factor = 1.0 - 2 * abs(t - 0.5)  # Linear from edges to center
                opening_y_offset = center_factor * opening_height/2
                
            elif phoneme_type.startswith('vowel_narrow'):  # Narrow shapes (i)
                # Narrow opening in the center
                center_factor = 1.0 - 8 * (t - 0.5) ** 2  # Sharp peak at center
                center_factor = max(0, center_factor)
                opening_y_offset = center_factor * opening_height/2
                
            else:  # Other consonants
                # Standard opening
                center_factor = 1.0 - 4 * (t - 0.5) ** 2  # Moderate peak at center
                center_factor = max(0, center_factor)
                opening_y_offset = center_factor * opening_height/2
            
            # Apply emotional width stretching to the opening
            width_stretch = (actual_width / base_width)
            if width_stretch > 1.0:  # Mouth is wider than normal
                # For wide emotions, make the opening extend more across the width
                edge_factor = 1.0 - 2 * abs(t - 0.5)  # 1 at center, 0 at edges
                width_opening_boost = (width_stretch - 1.0) * edge_factor * 0.3
                opening_y_offset += width_opening_boost * opening_height
            
            # Upper lip outer contour
            upper_outer_curve = math.sin(t * math.pi) * upper_curve_strength * actual_height
            upper_outer_y = cy + opening_y_offset/2 + upper_outer_curve + lip_thickness/2
            
            # Upper lip inner contour (mouth opening)
            upper_inner_y = cy + opening_y_offset/2
            
            # Lower lip inner contour (mouth opening)
            lower_inner_y = cy - opening_y_offset/2
            
            # Lower lip outer contour
            lower_outer_curve = math.sin(t * math.pi) * lower_curve_strength * actual_height
            lower_outer_y = cy - opening_y_offset/2 - lower_outer_curve - lip_thickness/2
            
            # Add vertices for triangle strip rendering
            # Each segment creates 4 vertices: upper_outer, upper_inner, lower_outer, lower_inner
            vertices.extend([
                (x, upper_outer_y),
                (x, upper_inner_y),
                (x, lower_outer_y),
                (x, lower_inner_y)
            ])
        
        return np.array(vertices, dtype=np.float32), actual_width

    def draw_dynamic_coordinated_mouth(self, vertices, color):
        """Draw the coordinated mouth with proper topology for realistic lips"""
        glDisable(GL_TEXTURE_2D)
        glColor4f(*color)
        
        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointer(2, GL_FLOAT, 0, vertices)
        
        segments = len(vertices) // 4 - 1  # Number of segments
        
        # Draw upper lip as quad strip
        upper_indices = []
        for i in range(segments):
            base_idx = i * 4
            next_base_idx = (i + 1) * 4
            # Create quad: current_outer, current_inner, next_inner, next_outer
            upper_indices.extend([
                base_idx,      # current upper outer
                base_idx + 1,  # current upper inner
                next_base_idx + 1,  # next upper inner
                next_base_idx       # next upper outer
            ])
        
        if upper_indices:
            glDrawElements(GL_QUADS, len(upper_indices), GL_UNSIGNED_INT, 
                          np.array(upper_indices, dtype=np.uint32))
        
        # Draw lower lip as quad strip
        lower_indices = []
        for i in range(segments):
            base_idx = i * 4
            next_base_idx = (i + 1) * 4
            # Create quad: current_inner, current_outer, next_outer, next_inner
            lower_indices.extend([
                base_idx + 3,  # current lower inner
                base_idx + 2,  # current lower outer
                next_base_idx + 2,  # next lower outer
                next_base_idx + 3   # next lower inner
            ])
        
        if lower_indices:
            glDrawElements(GL_QUADS, len(lower_indices), GL_UNSIGNED_INT, 
                          np.array(lower_indices, dtype=np.uint32))
        
        glDisableClientState(GL_VERTEX_ARRAY)
        glColor4f(1.0, 1.0, 1.0, 1.0)  # Reset to white
    
    def render_face(self, avatar_state):
        """Render the complete face with loading mode support"""
        # Update background color
        dt = time.time() - self.last_update_time
        self.update_background_color(avatar_state.is_loading, dt)
        self.last_update_time = time.time()
        
        glClear(GL_COLOR_BUFFER_BIT)
        glLoadIdentity()
        
        # Create meshes dynamically based on current window size
        face_v, face_tc = self.create_quad_mesh(self.center_x, self.center_y, self.face_width, self.face_height)
        
        # Eye backgrounds
        l_eye_v, l_eye_tc = self.create_quad_mesh(
            self.center_x - self.eye_x_offset, 
            self.center_y + self.eye_y_offset, 
            self.eye_size, self.eye_size * 0.8
        )
        r_eye_v, r_eye_tc = self.create_quad_mesh(
            self.center_x + self.eye_x_offset, 
            self.center_y + self.eye_y_offset, 
            self.eye_size, self.eye_size * 0.8
        )
        
        # Pupils
        l_pupil_v, l_pupil_tc = self.create_quad_mesh(
            self.center_x - self.eye_x_offset, 
            self.center_y + self.eye_y_offset, 
            self.pupil_size, self.pupil_size
        )
        r_pupil_v, r_pupil_tc = self.create_quad_mesh(
            self.center_x + self.eye_x_offset, 
            self.center_y + self.eye_y_offset, 
            self.pupil_size, self.pupil_size
        )
        
        # Eyebrows
        l_brow_v = self.create_curved_eyebrow_mesh(
            self.center_x - self.eye_x_offset, 
            self.center_y + self.brow_y_offset, 
            self.brow_size, self.eye_size * 0.05
        )
        r_brow_v = self.create_curved_eyebrow_mesh(
            self.center_x + self.eye_x_offset, 
            self.center_y + self.brow_y_offset, 
            self.brow_size, self.eye_size * 0.05
        )
        
        # Calculate movement ranges
        pupil_movement_range = np.array([self.eye_size * 0.15, self.eye_size * 0.1])
        
        # 1. Base Face
        if "base" in self.texture_manager.textures:
            self.draw_quad(face_v, face_tc, self.texture_manager.textures["base"])
        
        # 2. Eye Backgrounds with blink scaling
        eye_scale_y = avatar_state.eye_open_ratio
        if "l_eye_bg" in self.texture_manager.textures:
            self.draw_scaled_quad(l_eye_v, l_eye_tc, self.texture_manager.textures["l_eye_bg"], 1.0, eye_scale_y)
        if "r_eye_bg" in self.texture_manager.textures:
            self.draw_scaled_quad(r_eye_v, r_eye_tc, self.texture_manager.textures["r_eye_bg"], 1.0, eye_scale_y)
        
        # 3. Pupils with enhanced movement and sleep handling
        pupil_offset = avatar_state.pupil_pos * pupil_movement_range
        pupil_scale = avatar_state.pupil_size
        
        if avatar_state.is_sleeping:
            crop_top_amount = max(0.0, 1.0 - avatar_state.eye_open_ratio * 0.8)
            pupil_offset_y = pupil_offset[1] + self.eye_size * 0.22
            
            glPushMatrix()
            glTranslatef(pupil_offset[0], pupil_offset_y, 0)
            if "l_pupil" in self.texture_manager.textures:
                self.draw_cropped_quad(l_pupil_v, l_pupil_tc, self.texture_manager.textures["l_pupil"], crop_top=crop_top_amount)
            glPopMatrix()
            
            glPushMatrix()
            glTranslatef(pupil_offset[0], pupil_offset_y, 0)
            if "r_pupil" in self.texture_manager.textures:
                self.draw_cropped_quad(r_pupil_v, r_pupil_tc, self.texture_manager.textures["r_pupil"], crop_top=crop_top_amount)
            glPopMatrix()
        else:
            pupil_scale_y = pupil_scale * eye_scale_y
            
            glPushMatrix()
            glTranslatef(pupil_offset[0], pupil_offset[1], 0)
            if "l_pupil" in self.texture_manager.textures:
                self.draw_scaled_quad(l_pupil_v, l_pupil_tc, self.texture_manager.textures["l_pupil"], pupil_scale, pupil_scale_y)
            glPopMatrix()
            
            glPushMatrix()
            glTranslatef(pupil_offset[0], pupil_offset[1], 0)
            if "r_pupil" in self.texture_manager.textures:
                self.draw_scaled_quad(r_pupil_v, r_pupil_tc, self.texture_manager.textures["r_pupil"], pupil_scale, pupil_scale_y)
            glPopMatrix()
        
        # 4. Curved Eyebrows (keep same color always)
        y_offset = avatar_state.eyebrow_y * self.face_height
        rotation = avatar_state.eyebrow_r
        
        for brow_v, rot_dir in [(l_brow_v, 1), (r_brow_v, -1)]:
            glPushMatrix()
            center_x = np.mean(brow_v[::2, 0])
            center_y = np.mean(brow_v[::2, 1]) + y_offset
            
            glTranslatef(center_x, center_y, 0)
            glRotatef(rotation * rot_dir, 0, 0, 1)
            glTranslatef(-center_x, -center_y + y_offset, 0)
            
            adjusted_brow_v = np.copy(brow_v)
            adjusted_brow_v[:, 1] += y_offset
            
            # FIXED: Always use same color for eyebrows
            self.draw_curved_shape(adjusted_brow_v, LIP_EYEBROW_COLOR_GL)
            glPopMatrix()
        
        # 5. Enhanced Dynamic Coordinated Lip Rendering (NEW VERSION)
        curve_amount = avatar_state.mouth_curve
        current_phoneme = 'neutral'
        
        # Get current phoneme if speaking
        if avatar_state.is_speaking and avatar_state.speech_phonemes:
            elapsed = time.time() - avatar_state.speech_start_time
            phoneme_time = 0
            
            for phoneme_type, duration in avatar_state.speech_phonemes:
                if elapsed < phoneme_time + duration:
                    current_phoneme = phoneme_type
                    break
                phoneme_time += duration
        
        # Create dynamic coordinated mouth mesh with emotion-based width
        mouth_vertices, actual_mouth_width = self.create_dynamic_coordinated_mouth_mesh(
            self.center_x, 
            self.center_y - self.mouth_y_offset, 
            self.mouth_width, 
            self.mouth_height, 
            current_phoneme,
            curve_amount=curve_amount,
            emotion_name=avatar_state.target_emotion
        )
        
        # Draw coordinated mouth
        self.draw_dynamic_coordinated_mouth(mouth_vertices, LIP_EYEBROW_COLOR_GL)


class VoiceController:
    """Enhanced voice controller with local detection"""
    
    def __init__(self):
        self.wake_keywords = WAKE_WORDS
        self.sleep_keywords = SLEEP_WORDS
        self.local_detector = LocalVoiceDetector()
    def normalize_text(self, text):
        # Lowercase and remove punctuation
        return re.sub(r'[^\w\s]', '', text.lower())
    def check_voice_command(self, text):
        """Check if text contains wake or sleep commands as exact words or phrases"""
        normalized = self.normalize_text(text)
        words = normalized.split()
        text_str = ' '.join(words)

        for keyword in self.wake_keywords:
            if ' ' in keyword:  # phrase
                if keyword in text_str:
                    return 'wake'
            else:  # single word
                if keyword in words:
                    return 'wake'

        for keyword in self.sleep_keywords:
            if ' ' in keyword:
                if keyword in text_str:
                    return 'sleep'
            else:
                if keyword in words:
                    return 'sleep'

        return None
    
    def listen_for_wake_command(self):
        """Listen for wake command locally"""
        return self.local_detector.listen_for_wake_word()

class EnhancedRobotFaceSystem:
    """Main system class with all fixes implemented"""
    
    def __init__(self, width=800, height=600, api_url="https://aiec.guni.ac.in:8111", user_name="test_user", fullscreen=False):
        self.width = width
        self.height = height
        self.fullscreen = fullscreen
        self.api_url = api_url
        self.user_name = user_name
        
        # System state
        self.running = True
        self.clock = pygame.time.Clock()
        self.fps = 30
        
        # Voice control state
        self.is_sleeping = True  # Start in sleep mode
        self.conversation_active = False
        self.audio_thread = None
        self.wake_listener_thread = None
        self.min_input_length = 5
        
        # Text display
        self.current_ai_text = ""
        self.text_display_time = 0
        self.text_fade_duration = 10.0
        self.display_text = True
        
        # Loading state
        self.is_loading = False
        self.loading_message = ""
        
        # Initialize pygame and display
        self.initialize_display()
        
        # Start in sleep mode and begin listening for wake commands
        self.set_expression("sleepy")
        self.start_wake_listener()
        
        print("Enhanced Robot Face System initialized!")
        print("🎙️ Say 'wake up' or 'hello' to start interacting!")
        self.print_controls()
    
    def initialize_display(self):
        """Initialize pygame and OpenGL display"""
        pygame.init()
        pygame.mixer.init()
        
        # Set display mode
        if self.fullscreen:
            display_info = pygame.display.Info()
            self.width = display_info.current_w
            self.height = display_info.current_h
            pygame.display.set_mode((self.width, self.height), DOUBLEBUF | OPENGL | FULLSCREEN)
        else:
            pygame.display.set_mode((self.width, self.height), DOUBLEBUF | OPENGL | RESIZABLE)
        
        pygame.display.set_caption("Enhanced Robot Face - Voice Controlled (Fixed)")
        
        # Initialize components
        self.texture_manager = TextureManager()
        self.face_renderer = FaceRenderer(self.width, self.height, self.texture_manager)
        self.voice_assistant = VoiceAssistantClient(self.api_url, self.user_name)
        self.voice_controller = VoiceController()
        self.avatar_state = AvatarState()
        
        # Initialize OpenGL with normal background
        glClearColor(*BG_COLOR_NORMAL)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluOrtho2D(0, self.width, 0, self.height)
        glMatrixMode(GL_MODELVIEW)
        
        # Update face renderer dimensions
        self.face_renderer.resize_window(self.width, self.height)
        
        logger.info("Display initialized successfully")
    
    def start_loading_mode(self, message="Connecting to server..."):
        """Start loading mode with funny expressions"""
        self.is_loading = True
        self.loading_message = message
        self.avatar_state.is_loading = True
        self.avatar_state.loading_start_time = time.time()
        self.avatar_state.loading_expression_index = 0
        self.avatar_state.next_loading_change = time.time() + 0.8
        
        # Set initial loading expression
        self.set_expression(LOADING_EXPRESSIONS[0])
        logger.info(f"Loading mode started: {message}")
    
    def stop_loading_mode(self):
        """Stop loading mode"""
        self.is_loading = False
        self.avatar_state.is_loading = False
        logger.info("Loading mode stopped")
    
    def update_loading_expressions(self):
        """Update loading expressions continuously"""
        if not self.avatar_state.is_loading:
            return
        
        current_time = time.time()
        if current_time > self.avatar_state.next_loading_change:
            # Cycle through loading expressions
            self.avatar_state.loading_expression_index = (self.avatar_state.loading_expression_index + 1) % len(LOADING_EXPRESSIONS)
            next_expression = LOADING_EXPRESSIONS[self.avatar_state.loading_expression_index]
            self.set_expression(next_expression)
            
            # Random timing for more natural feel
            self.avatar_state.next_loading_change = current_time + random.uniform(0.6, 1.2)
            
            logger.info(f"Loading expression changed to: {next_expression}")
    
    def start_wake_listener(self):
        """Start the wake word listener thread"""
        if not self.wake_listener_thread or not self.wake_listener_thread.is_alive():
            self.wake_listener_thread = threading.Thread(target=self.wake_listener_worker)
            self.wake_listener_thread.daemon = True
            self.wake_listener_thread.start()
            logger.info("Wake listener started")
    
    def wake_listener_worker(self):
        """Worker thread for listening to wake commands"""
        while self.running:
            if self.is_sleeping and not self.conversation_active:
                try:
                    result = self.voice_controller.listen_for_wake_command()
                    if result is True:  # Wake command detected
                        logger.info("Wake command detected locally")
                        self.wake_up()
                    elif result is False:  # Sleep command detected (but already sleeping)
                        pass
                except Exception as e:
                    logger.error(f"Wake listener error: {e}")
                
                time.sleep(0.1)  # Small delay to prevent excessive CPU usage
            else:
                time.sleep(1)  # Longer delay when not needed
    
    def set_expression(self, emotion_name):
        """Set facial expression"""
        if emotion_name in EMOTIONS:
            self.avatar_state.target_emotion = emotion_name
            logger.info(f"Expression set to: {emotion_name}")
        else:
            logger.warning(f"Unknown emotion: {emotion_name}")
    
    def update_animations(self, dt):
        """Update all animations with loading mode support"""
        current_time = time.time()
        speed = dt * self.avatar_state.emotion_transition_speed
        
        # Update loading expressions
        self.update_loading_expressions()
        
        # Get current emotion parameters
        emotion = EMOTIONS[self.avatar_state.target_emotion]
        
        # Update emotion targets
        self.avatar_state.target_eyebrow_y = emotion["eyebrow_y"]
        self.avatar_state.target_eyebrow_r = emotion["eyebrow_r"]
        self.avatar_state.target_mouth_curve = emotion["mouth_c"]
        self.avatar_state.target_eye_open_ratio = emotion["eye_o"]
        self.avatar_state.target_pupil_size = emotion["pupil_s"]
        self.avatar_state.eye_movement_range = emotion["eye_move_range"]
        
        # Smooth transitions
        self.avatar_state.eyebrow_y += (self.avatar_state.target_eyebrow_y - self.avatar_state.eyebrow_y) * speed
        self.avatar_state.eyebrow_r += (self.avatar_state.target_eyebrow_r - self.avatar_state.eyebrow_r) * speed
        self.avatar_state.mouth_curve += (self.avatar_state.target_mouth_curve - self.avatar_state.mouth_curve) * speed
        self.avatar_state.pupil_size += (self.avatar_state.target_pupil_size - self.avatar_state.pupil_size) * speed
        
        # Eye movement control
        self.avatar_state.eye_movement_enabled = not emotion.get("eye_steady", False)
        self.avatar_state.is_sleeping = (self.avatar_state.target_emotion == "sleepy")
        
        # Enhanced pupil movement for loading mode
        if self.avatar_state.is_loading:
            # Crazy eye movement during loading
            loading_time = current_time - self.avatar_state.loading_start_time
            self.avatar_state.target_pupil_pos = np.array([
                math.sin(loading_time * 3) * 0.8,
                math.cos(loading_time * 2.5) * 0.6
            ])
        elif self.avatar_state.eye_movement_enabled and current_time > self.avatar_state.next_gaze_shift_time:
            movement_range = self.avatar_state.eye_movement_range
            self.avatar_state.target_pupil_pos = np.array([
                random.uniform(-movement_range, movement_range), 
                random.uniform(-movement_range * 0.7, movement_range * 0.7)
            ])
            self.avatar_state.next_gaze_shift_time = current_time + random.uniform(1.5, 4.0)
        elif not self.avatar_state.eye_movement_enabled:
            self.avatar_state.target_pupil_pos = np.array([0.0, 0.0])
        
        self.avatar_state.pupil_pos += (self.avatar_state.target_pupil_pos - self.avatar_state.pupil_pos) * dt * 3.0
        
        # Breathing animation
        self.avatar_state.breathing_offset = math.sin(current_time * 2) * 3
        
        # Sleep animation
        if self.avatar_state.is_sleeping:
            self.avatar_state.sleep_animation_phase += dt * 2.0
            sleep_offset = math.sin(self.avatar_state.sleep_animation_phase) * 0.05
            self.avatar_state.pupil_pos[1] = sleep_offset
        
        # Enhanced blinking system
        if not self.avatar_state.is_blinking and current_time > self.avatar_state.next_blink_time:
            self.avatar_state.is_blinking = True
            self.avatar_state.blink_start_time = current_time
            
            if self.avatar_state.is_sleeping:
                self.avatar_state.blink_duration = 2.0
            elif self.avatar_state.target_emotion in ["fear", "surprise"]:
                self.avatar_state.blink_duration = 0.08
            else:
                self.avatar_state.blink_duration = 0.12
        
        if self.avatar_state.is_blinking:
            progress = (current_time - self.avatar_state.blink_start_time) / self.avatar_state.blink_duration
            if progress <= 1.0:
                if self.avatar_state.is_sleeping:
                    self.avatar_state.eye_open_ratio = 0.3 + math.sin(progress * math.pi) * 0.1
                else:
                    self.avatar_state.eye_open_ratio = 1.0 - math.sin(progress * math.pi) * 0.8
            else:
                self.avatar_state.is_blinking = False
                self.avatar_state.eye_open_ratio = self.avatar_state.target_eye_open_ratio
                if self.avatar_state.is_sleeping:
                    self.avatar_state.next_blink_time = current_time + random.uniform(0.5, 2.0)
                else:
                    self.avatar_state.next_blink_time = current_time + random.uniform(2, 6)
        else:
            self.avatar_state.eye_open_ratio += (self.avatar_state.target_eye_open_ratio - self.avatar_state.eye_open_ratio) * speed
        
        # Enhanced coordinated lip sync with dynamic width (UPDATED SECTION)
        if self.avatar_state.is_speaking and self.avatar_state.speech_phonemes:
            elapsed = current_time - self.avatar_state.speech_start_time
            
            phoneme_time = 0
            current_phoneme = None
            
            for phoneme_type, duration in self.avatar_state.speech_phonemes:
                if elapsed < phoneme_time + duration:
                    current_phoneme = phoneme_type
                    break
                phoneme_time += duration
            
            # Set mouth opening ratio and width based on current phoneme
            if current_phoneme:
                if current_phoneme.startswith('vowel_wide'):
                    self.avatar_state.mouth_open_ratio = 0.9
                    self.avatar_state.target_mouth_width = 1.3  # Wider for "ah", "eh"
                elif current_phoneme.startswith('vowel_round'):
                    self.avatar_state.mouth_open_ratio = 0.7
                    self.avatar_state.target_mouth_width = 0.8  # Narrower for "oh", "oo"
                elif current_phoneme.startswith('vowel_narrow'):
                    self.avatar_state.mouth_open_ratio = 0.4
                    self.avatar_state.target_mouth_width = 0.7  # Much narrower for "ee"
                elif current_phoneme.startswith('bilabial'):
                    self.avatar_state.mouth_open_ratio = 0.0
                    self.avatar_state.target_mouth_width = 1.0  # Normal width
                elif current_phoneme.startswith('dental'):
                    self.avatar_state.mouth_open_ratio = 0.4
                    self.avatar_state.target_mouth_width = 1.0  # Normal width
                elif current_phoneme.startswith('sibilant'):
                    self.avatar_state.mouth_open_ratio = 0.3
                    self.avatar_state.target_mouth_width = 0.85  # Slightly narrow
                elif current_phoneme.startswith('rounded'):
                    self.avatar_state.mouth_open_ratio = 0.5
                    self.avatar_state.target_mouth_width = 0.8  # Narrow and round
                else:  # pause or other
                    self.avatar_state.mouth_open_ratio = 0.1
                    self.avatar_state.target_mouth_width = 1.0
                
                # Add natural variation for more realistic movement
                variation = math.sin(elapsed * math.pi * 4) * 0.1
                self.avatar_state.mouth_open_ratio += variation
                self.avatar_state.mouth_open_ratio = max(0.0, min(1.0, self.avatar_state.mouth_open_ratio))
                
                # Add width variation for dynamic speech
                width_variation = math.sin(elapsed * math.pi * 3) * 0.05
                self.avatar_state.target_mouth_width += width_variation
        else:
            # Return to neutral position when not speaking
            self.avatar_state.mouth_open_ratio *= max(0, 1.0 - (dt * 4.0))
            # Return to emotion-based default width
            emotion_defaults = {
                'happy': 1.2, 'amusement': 1.3, 'love': 1.1,
                'sad': 0.8, 'angry': 0.9, 'fear': 0.8,
                'surprise': 1.1, 'disgust': 0.8,
                'neutral': 1.0
            }
            self.avatar_state.target_mouth_width = emotion_defaults.get(
                self.avatar_state.target_emotion, 1.0
            )
        
        # Smooth width transitions
        self.avatar_state.current_mouth_width += (
            self.avatar_state.target_mouth_width - self.avatar_state.current_mouth_width
        ) * dt * 8.0  # Fast width changes for responsive speech
    
    def handle_events(self):
        """Handle pygame events including window resize"""
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False
            elif event.type == VIDEORESIZE:
                self.width = event.w
                self.height = event.h
                self.face_renderer.resize_window(self.width, self.height)
                logger.info(f"Window resized to: {self.width}x{self.height}")
            elif event.type == KEYDOWN:
                self.handle_key_press(event.key)
    
    def handle_key_press(self, key):
        """Handle keyboard input"""
        # Emotion keys
        emotion_keys = {
            K_1: "happy", K_2: "sad", K_3: "angry", K_4: "surprise",
            K_5: "fear", K_6: "disgust", K_7: "amusement", K_8: "frustration",
            K_9: "embarrassment", K_0: "neutral", K_l: "love", K_c: "confusion"
        }
        
        if key in emotion_keys:
            self.set_expression(emotion_keys[key])
        elif key == K_ESCAPE:
            self.running = False
        elif key == K_w:
            if self.is_sleeping:
                self.wake_up()
        elif key == K_s:
            if not self.is_sleeping:
                self.enter_sleep_mode()
        elif key == K_SPACE:
            if not self.conversation_active and not self.is_sleeping:
                self.start_conversation_mode()
        elif key == K_t:
            self.display_text = not self.display_text
            logger.info(f"Text display {'enabled' if self.display_text else 'disabled'}")
        elif key == K_F11:
            self.toggle_fullscreen()
    
    def toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            display_info = pygame.display.Info()
            self.width = display_info.current_w
            self.height = display_info.current_h
            pygame.display.set_mode((self.width, self.height), DOUBLEBUF | OPENGL | FULLSCREEN)
        else:
            self.width = 800
            self.height = 600
            pygame.display.set_mode((self.width, self.height), DOUBLEBUF | OPENGL | RESIZABLE)
        
        self.face_renderer.resize_window(self.width, self.height)
        logger.info(f"Fullscreen {'enabled' if self.fullscreen else 'disabled'}")
    
    def start_conversation_mode(self):
        """Start voice conversation mode"""
        if not self.conversation_active and not self.is_sleeping:
            logger.info("Starting conversation mode")
            self.conversation_active = True
            self.set_expression("happy")
            
            self.audio_thread = threading.Thread(target=self.conversation_worker)
            self.audio_thread.daemon = True
            self.audio_thread.start()
            
            print("🎤 Voice conversation started! Speak to interact.")
    
    def conversation_worker(self):
        """Worker function for voice conversation with loading support"""
        try:
            while self.running and self.conversation_active and not self.is_sleeping:
                logger.info("Listening for voice input...")
                
                # Set listening expression
                self.set_expression("happy")
                
                # Record audio with minimum time
                self.voice_assistant.is_recording = True
                self.voice_assistant.is_processing = False
                self.voice_assistant.is_speaking = False
                
                audio_path = self.voice_assistant.record_audio_with_minimum_time()
                self.voice_assistant.is_recording = False
                
                if not audio_path:
                    logger.error("Failed to record audio")
                    time.sleep(2)
                    continue
                
                # Process with API - show loading
                logger.info("Processing with API...")
                self.start_loading_mode("Processing your request...")
                self.voice_assistant.is_processing = True
                
                response_data = self.voice_assistant.send_audio_to_api(audio_path)
                self.voice_assistant.is_processing = False
                self.stop_loading_mode()
                
                if not response_data:
                    logger.error("Failed to get API response")
                    self.set_expression("confusion")
                    time.sleep(2)
                    continue
                
                # Extract data
                user_input = response_data.get('user_input', '')
                text_response = response_data.get('text_response', '')
                robot_expression = response_data.get('robot_expression', 'happy')
                
                # Check for voice commands in response
                voice_command = self.voice_controller.check_voice_command(text_response)
                if voice_command == 'sleep':
                    logger.info("Sleep command detected")
                    self.enter_sleep_mode()
                    break
                elif voice_command == 'wake':
                    logger.info("Wake command detected (already awake)")
                    self.set_expression("surprise")
                    time.sleep(1)
                else:
                    voice_command = self.voice_controller.check_voice_command(user_input)
                    if voice_command == 'sleep':
                        logger.info("Sleep command detected")
                        self.enter_sleep_mode()
                        break
                    elif voice_command == 'wake':
                        logger.info("Wake command detected (already awake)")
                        self.set_expression("surprise")
                        time.sleep(1)
                    
                
                # Store conversation
                self.voice_assistant.store_conversation(
                    user_input, text_response, 
                    response_data.get('language_used', 'english')
                )
                
                # Update text display
                self.current_ai_text = text_response
                self.text_display_time = time.time()
                
                # Play response with enhanced lip sync
                self.set_expression("talking")
                self.voice_assistant.is_speaking = True
                self.voice_assistant.play_audio_response(response_data, self.avatar_state)
                self.voice_assistant.is_speaking = False
                
                # Set final expression
                if robot_expression == "sleepy":
                    self.enter_sleep_mode()
                    break
                
                self.set_expression(robot_expression)
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"Conversation worker error: {e}")
            self.conversation_active = False
            self.stop_loading_mode()
    
    def enter_sleep_mode(self):
        """Enter sleep mode"""
        logger.info("Entering sleep mode...")
        self.is_sleeping = True
        self.conversation_active = False
        self.set_expression("sleepy")
        self.stop_loading_mode()
        
        # Reset voice assistant states
        self.voice_assistant.is_recording = False
        self.voice_assistant.is_processing = False
        self.voice_assistant.is_speaking = False
        
        # Restart wake listener
        self.start_wake_listener()
        
        print("😴 Robot is sleeping. Say 'wake up' or 'hello' to wake it up!")
    
    def wake_up(self):
        """Wake up from sleep mode"""
        if self.is_sleeping:
            logger.info("Waking up...")
            self.is_sleeping = False
            self.set_expression("surprise")
            time.sleep(0.5)
            self.set_expression("happy")
            self.start_conversation_mode()  # Automatically start conversation
            print("😊 Robot is awake! Speaking...")
    
    def render_text_overlay(self, text, alpha=1.0):
        """Render text overlay"""
        if not text or alpha <= 0:
            return
        
        # Set up 2D rendering
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.width, 0, self.height, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        # Draw background box
        text_lines = self.wrap_text(text, 60)
        line_count = len(text_lines)
        
        bg_height = max(80, line_count * 25 + 20)
        bg_width = min(self.width - 40, 600)
        bg_x = (self.width - bg_width) // 2
        bg_y = 20
        
        # Background
        glColor4f(0.0, 0.0, 0.0, 0.7 * alpha)
        glBegin(GL_QUADS)
        glVertex2f(bg_x, bg_y)
        glVertex2f(bg_x + bg_width, bg_y)
        glVertex2f(bg_x + bg_width, bg_y + bg_height)
        glVertex2f(bg_x, bg_y + bg_height)
        glEnd()
        
        # Border with different color for loading mode
        if self.is_loading:
            glColor4f(1.0, 0.5, 0.0, alpha)  # Orange for loading
        else:
            glColor4f(0.3, 0.6, 1.0, alpha)  # Blue for normal
        
        glLineWidth(2.0)
        glBegin(GL_LINE_LOOP)
        glVertex2f(bg_x, bg_y)
        glVertex2f(bg_x + bg_width, bg_y)
        glVertex2f(bg_x + bg_width, bg_y + bg_height)
        glVertex2f(bg_x, bg_y + bg_height)
        glEnd()
        
        # Restore matrices
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
    
    def wrap_text(self, text, width):
        """Wrap text to specified width"""
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            if len(current_line + " " + word) <= width:
                if current_line:
                    current_line += " " + word
                else:
                    current_line = word
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        return lines
    
    def render_status_overlay(self):
        """Render status information"""
        # Display loading message
        if self.is_loading and self.loading_message:
            self.render_text_overlay(f"🔄 {self.loading_message}", 1.0)
        
        # Display AI text if available
        elif self.current_ai_text and self.display_text:
            current_time = time.time()
            elapsed_time = current_time - self.text_display_time
            
            if elapsed_time < self.text_fade_duration:
                fade_factor = max(0.0, 1.0 - (elapsed_time / self.text_fade_duration))
                self.render_text_overlay(self.current_ai_text, fade_factor)
        
        # Show wake instruction when sleeping
        elif self.is_sleeping:
            self.render_text_overlay("😴 Say 'wake up' or 'hello' to wake me!", 0.8)
    
    def render_frame(self):
        """Render a complete frame"""
        self.face_renderer.render_face(self.avatar_state)
        #self.render_status_overlay()
        pygame.display.flip()
    
    def run(self):
        """Main run loop"""
        logger.info("Starting Enhanced Robot Face System...")
        
        while self.running:
            dt = self.clock.tick(self.fps) / 1000.0
            
            self.handle_events()
            self.update_animations(dt)
            self.render_frame()
        
        self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up...")
        
        self.conversation_active = False
        self.is_sleeping = True
        
        # Stop voice assistant
        self.voice_assistant.is_recording = False
        self.voice_assistant.is_processing = False
        self.voice_assistant.is_speaking = False
        
        # Stop audio
        try:
            pygame.mixer.music.stop()
        except:
            pass
        
        # Wait for threads
        if self.audio_thread and self.audio_thread.is_alive():
            self.audio_thread.join(timeout=2.0)
        
        if self.wake_listener_thread and self.wake_listener_thread.is_alive():
            self.wake_listener_thread.join(timeout=2.0)
        
        pygame.quit()
        logger.info("System shutdown complete")
    
    def print_controls(self):
        """Print control instructions"""
        print("\n" + "="*70)
        print("🎮 ENHANCED ROBOT FACE CONTROLS (FIXED VERSION):")
        print("="*70)
        print("VOICE INTERACTION:")
        print("  🎙️  Say 'wake up' or 'hello' to wake the robot")
        print("  💤 Say 'sleep' or 'goodbye' to put robot to sleep")
        print("  🗣️  Robot automatically starts conversation when awake")
        print()
        print("EMOTIONS (Manual Override):")
        print("  1-9, 0: Happy, Sad, Angry, Surprise, Fear, Disgust, Amusement, Frustration, Embarrassment, Neutral")
        print("  L: Love    C: Confusion")
        print()
        print("SYSTEM CONTROLS:")
        print("  SPACE: Force start conversation (if awake)")
        print("  W: Force wake up (keyboard override)")
        print("  S: Force sleep mode (keyboard override)")
        print("  T: Toggle text display")
        print("  F11: Toggle fullscreen")
        print("  ESC: Quit")
        print()
        print("IMPROVEMENTS:")
        print("  ✅ Fixed color consistency during speech")
        print("  ✅ Enhanced phoneme-based lip sync (o, a, e, i, u)")
        print("  ✅ Voice-controlled wake/sleep")
        print("  ✅ Automatic conversation start")
        print("  ✅ Local wake word detection")
        print("  ✅ Minimum recording time guaranteed")
        print("  ✅ Interactive loading animations")
        print("  ✅ Background color changes (blue=normal, black=loading)")
        print("="*70)

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Enhanced Robot Face System - Fixed Version')
    parser.add_argument('--api-url', default='https://aiec.guni.ac.in:8111', 
                      help='API server URL')
    parser.add_argument('--user-name', default='test_user',
                      help='User name for conversations')
    parser.add_argument('--width', type=int, default=800,
                      help='Window width')
    parser.add_argument('--height', type=int, default=600,
                      help='Window height')
    parser.add_argument('--fullscreen', action='store_true',
                      help='Start in fullscreen mode')
    
    args = parser.parse_args()
    
    try:
        system = EnhancedRobotFaceSystem(
            width=args.width,
            height=args.height,
            api_url=args.api_url,
            user_name=args.user_name,
            fullscreen=args.fullscreen
        )
        
        system.run()
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info("Enhanced Robot Face System shutting down...")
        robot.release_all()

if __name__ == "__main__":
    main()