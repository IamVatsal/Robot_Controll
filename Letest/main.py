import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
from PIL import Image
import math
import time
import threading
import os
import random
import re
import wave
import contextlib
import requests
import tempfile
import pyaudio
import wave
import argparse
import logging
import urllib.parse
import struct
import urllib3
from typing import Dict, List, Tuple, Optional, Any

# Disable SSL warnings (only if you need to use verify=False)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    import pygame
    from pygame.locals import *
    from OpenGL.GL import *
    from OpenGL.GLU import *
except ImportError as e:
    print(f"Required libraries not installed: {e}")
    print("Install with: pip install pygame PyOpenGL PyOpenGL_accelerate requests pyaudio")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

expp = "cute_neutral"

class VoiceAssistantClient:
    """Voice Assistant Client for API Communication"""
    
    def __init__(self, api_url=" https://aiec.guni.ac.in:8111", user_name="test_user", verify_ssl=False):
        self.api_url = api_url
        self.user_name = user_name
        self.verify_ssl = verify_ssl
        
        # Audio Configuration
        self.audio_config = {
            'chunk': 1024,
            'format': pyaudio.paInt16,
            'channels': 1,
            'rate': 16000,
            'record_seconds': 5
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
    
    def store_conversation(self, user_input, ai_response, language_used='english'):
        """Store conversation in the server database"""
        try:
            if not user_input or not ai_response:
                logger.warning("Skipping conversation storage - missing user input or AI response")
                return False
            
            logger.info(f"Storing conversation for user: {self.user_name}")
            logger.info(f"User input: {user_input[:100]}...")
            logger.info(f"AI response: {ai_response[:100]}...")
            
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
                    logger.info("Conversation stored successfully in server database")
                    return True
                else:
                    logger.warning(f"Failed to store conversation: {result}")
                    return False
            else:
                logger.error(f"Failed to store conversation: HTTP {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            logger.error("Timeout while storing conversation")
            return False
        except requests.exceptions.SSLError as e:
            logger.error(f"SSL Certificate error while storing conversation: {e}")
            return False
        except requests.exceptions.ConnectionError:
            logger.error("Connection error while storing conversation")
            return False
        except Exception as e:
            logger.error(f"Error storing conversation: {e}")
            return False
    
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
            logger.info("Consider setting verify_ssl=False if using self-signed certificates")
        except requests.exceptions.RequestException as e:
            self.api_status = "Connection Error"
            logger.error(f"Cannot connect to API at {self.api_url}: {e}")
    
    def record_audio(self):
        """Record audio from microphone"""
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
            
            logger.info("Recording started...")
            frames = []
            
            for _ in range(0, int(self.audio_config['rate'] / self.audio_config['chunk'] * self.audio_config['record_seconds'])):
                if not self.is_recording:
                    break
                data = stream.read(self.audio_config['chunk'], exception_on_overflow=False)
                frames.append(data)
            
            stream.stop_stream()
            stream.close()
            audio.terminate()
            
            logger.info("Recording finished.")
            
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
                files = {
                    'audio': ('audio.wav', audio_file, 'audio/wav')
                }
                data = {
                    'user_name': self.user_name
                }
                
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
            
            logger.info(f"API Response Status: {response.status_code}")
            logger.info(f"API Response Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                # The new API returns audio content directly with headers
                import urllib.parse
                
                robot_expression = response.headers.get('X-Robot-Expression', 'cute_neutral')
                encoded_text_response = response.headers.get('X-LLM-Text', 'I am here to help!')
                language_used = response.headers.get('X-Language-Used', 'english')
                audio_format = response.headers.get('X-Audio-Format', 'mp3')
                
                # Decode the URL-encoded text response
                try:
                    text_response = urllib.parse.unquote(encoded_text_response)
                except Exception as decode_error:
                    logger.warning(f"Failed to decode text response: {decode_error}")
                    text_response = encoded_text_response  # Use as-is if decoding fails
                
                # Save audio content to temp file with correct extension
                file_extension = '.wav' if audio_format == 'wav' else '.mp3'
                temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
                temp_audio.write(response.content)
                temp_audio.close()
                
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
                logger.error(f"Response content: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("API request timed out")
            return None
        except requests.exceptions.SSLError as e:
            logger.error(f"SSL Certificate error during API request: {e}")
            return None
        except requests.exceptions.ConnectionError:
            logger.error("Failed to connect to API")
            return None
        except Exception as e:
            logger.error(f"API communication error: {e}")
            return None
    
    def play_audio_response(self, response_data):
        """Play audio response from API"""
        if not response_data:
            logger.error("No response data to play audio from")
            return
        
        if 'audio_file' in response_data and response_data['audio_file']:
            try:
                audio_file_path = response_data['audio_file']
                audio_format = response_data.get('audio_format', 'mp3')
                
                logger.info(f"Playing {audio_format} audio file: {audio_file_path}")
                
                # Initialize pygame mixer with appropriate settings based on format
                try:
                    pygame.mixer.quit()  # Ensure clean state
                except:
                    pass
                
                # Different settings for WAV vs MP3
                if audio_format == 'wav':
                    # More compatible settings for WAV files, especially pyttsx3 generated ones
                    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=1024)
                else:
                    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
                
                # Load and play audio
                try:
                    pygame.mixer.music.load(audio_file_path)
                    avatar_state.target_emotion = emotion
                    avatar_state.is_speaking = True
                    avatar_state.speech_start_time = time.time()
                    avatar_state.speech_text = text
                    avatar_state.speech_phonemes = text_to_phonemes(text)
                    avatar_state.current_phoneme_index = 0
                    pygame.mixer.music.play()
                    
                    logger.info(f"Audio playback started ({audio_format} format)")
                    
                    # Wait for playback to complete
                    while pygame.mixer.music.get_busy():
                        pygame.time.Clock().tick(10)
                        if not self.is_speaking:
                            pygame.mixer.music.stop()
                            break
                    avatar_state.is_speaking = False
                    avatar_state.mouth_open_ratio = 0.0
                    avatar_state.upper_lip_y = 0.0
                    avatar_state.lower_lip_y = 0.0
                    logger.info("Audio playback completed")
                except pygame.error as e:
                    logger.error(f"Pygame audio error: {e}")
                    
                    # Enhanced alternative playback method for WAV files
                    if audio_format == 'wav':
                        try:
                            logger.info("Trying alternative WAV playback method with different settings")
                            # Try different mixer settings for problematic WAV files
                            pygame.mixer.quit()
                            pygame.mixer.init(frequency=16000, size=-16, channels=1, buffer=2048)
                            
                            sound = pygame.mixer.Sound(audio_file_path)
                            avatar_state.target_emotion = emotion
                            avatar_state.is_speaking = True
                            avatar_state.speech_start_time = time.time()
                            avatar_state.speech_text = text
                            avatar_state.speech_phonemes = text_to_phonemes(text)
                            avatar_state.current_phoneme_index = 0
                            sound.play()
                            
                            # Wait for sound to finish
                            while pygame.mixer.get_busy():
                                pygame.time.Clock().tick(10)
                                if not self.is_speaking:
                                    pygame.mixer.stop()
                                    break
                            avatar_state.is_speaking = False
                            avatar_state.mouth_open_ratio = 0.0
                            avatar_state.upper_lip_y = 0.0
                            avatar_state.lower_lip_y = 0.0
                            logger.info("Alternative WAV playback completed")
                        except Exception as alt_error:
                            logger.error(f"Alternative WAV playback failed: {alt_error}")
                            
                            # Final fallback - try with default pygame settings
                            try:
                                logger.info("Trying final fallback WAV playback method")
                                pygame.mixer.quit()
                                pygame.mixer.init()  # Use default settings
                                
                                sound = pygame.mixer.Sound(audio_file_path)
                                sound.play()
                                
                                while pygame.mixer.get_busy():
                                    pygame.time.Clock().tick(10)
                                    if not self.is_speaking:
                                        pygame.mixer.stop()
                                        break
                                
                                logger.info("Final fallback WAV playback completed")
                            except Exception as final_error:
                                logger.error(f"All WAV playback methods failed: {final_error}")
                    else:
                        logger.error(f"MP3 playback failed: {e}")
                
                # Cleanup temp file
                try:
                    os.unlink(audio_file_path)
                except:
                    pass
                    
            except Exception as e:
                logger.error(f"Audio playback error: {e}")
        else:
            logger.warning("No audio_file in response data")
            # If there's text response but no audio, at least log it
            if 'text_response' in response_data:
                logger.info(f"Text response (no audio): {response_data['text_response']}")
# --- Configuration ---
WINDOW_WIDTH = 300
WINDOW_HEIGHT = 200
PARTS_PATH = "parts/" # Assumes a 'parts' subfolder for images

# Color for lips and eyebrows
LIP_EYEBROW_COLOR = (0, 53, 86)  # #003556 in RGB
LIP_EYEBROW_COLOR_GL = (0/255.0, 53/255.0, 86/255.0, 1.0)  # Normalized for OpenGL

# --- Emotion Definitions ---
EMOTIONS = {
    "neutral":     {"eyebrow_y": 0.0,  "eyebrow_r": 0,   "mouth_c": 0.0,  "eye_o": 1.0, "pupil_s": 1.0, "eye_steady": False, "eye_move_range": 0.3},
    "happy":       {"eyebrow_y": 0.05, "eyebrow_r": -5,  "mouth_c": 0.0,  "eye_o": 1.0, "pupil_s": 1.0, "eye_steady": False, "eye_move_range": 0.4},
    "sad":         {"eyebrow_y": -0.03,"eyebrow_r": 15,  "mouth_c": -0.7, "eye_o": 0.6, "pupil_s": 0.9, "eye_steady": False, "eye_move_range": 0.2},
    "angry":       {"eyebrow_y": -0.01,"eyebrow_r": -10, "mouth_c": -0.4, "eye_o": 0.9, "pupil_s": 1.0, "eye_steady": False, "eye_move_range": 0.5},
    "surprise":    {"eyebrow_y": 0.12, "eyebrow_r": 5,   "mouth_c": 0.2,  "eye_o": 1.1, "pupil_s": 0.8, "eye_steady": False, "eye_move_range": 0.6},
    "fear":        {"eyebrow_y": 0.1,  "eyebrow_r": 20,  "mouth_c": -0.5, "eye_o": 1.15,"pupil_s": 0.7, "eye_steady": False, "eye_move_range": 0.7},
    "disgust":     {"eyebrow_y": -0.02,"eyebrow_r": -5,  "mouth_c": -0.6, "eye_o": 0.9, "pupil_s": 1.0, "eye_steady": False, "eye_move_range": 0.3},
    "amusement":   {"eyebrow_y": 0.04, "eyebrow_r": -4,  "mouth_c": 0.6,  "eye_o": 1.0, "pupil_s": 1.0, "eye_steady": False, "eye_move_range": 0.4},
    "frustration": {"eyebrow_y": -0.01,"eyebrow_r": -5,  "mouth_c": -0.3, "eye_o": 0.9, "pupil_s": 1.0, "eye_steady": False, "eye_move_range": 0.4},
    "love":        {"eyebrow_y": 0.03, "eyebrow_r": -6,  "mouth_c": 0.5,  "eye_o": 1.0, "pupil_s": 1.2, "eye_steady": False, "eye_move_range": 0.3},
    "embarrassment":{"eyebrow_y":-0.02,"eyebrow_r": 5,   "mouth_c": -0.2, "eye_o": 0.8, "pupil_s": 1.1, "eye_steady": False, "eye_move_range": 0.2},
    "confusion":   {"eyebrow_y": 0.0,  "eyebrow_r": 15,  "mouth_c": -0.1, "eye_o": 0.9, "pupil_s": 1.0, "eye_steady": False, "eye_move_range": 0.5},
    "sleep":       {"eyebrow_y": -0.01,"eyebrow_r": 2,   "mouth_c": 0.1,  "eye_o": 0.2, "pupil_s": 0.1, "eye_steady": True, "eye_move_range": 0.1},
}



# --- Global Animation State ---
class AvatarState:
    def __init__(self):
        self.target_emotion = "neutral"
        self.current_emotion = "neutral"
        self.emotion_transition_speed = 3.0
        self.eye_open_ratio = 1.0
        self.target_eye_open_ratio = 1.0
        self.is_blinking = False
        self.blink_start_time = 0
        self.blink_duration = 0.12
        self.next_blink_time = time.time() + 3
        self.eyebrow_y, self.target_eyebrow_y = 0.0, 0.0
        self.eyebrow_r, self.target_eyebrow_r = 0.0, 0.0
        self.pupil_pos = np.array([0.0, 0.0])
        self.target_pupil_pos = np.array([0.0, 0.0])
        self.next_gaze_shift_time = time.time() + 2
        self.pupil_size, self.target_pupil_size = 1.0, 1.0
        self.mouth_open_ratio = 0.0
        self.mouth_curve, self.target_mouth_curve = 0.0, 0.0
        self.upper_lip_y = 0.0
        self.lower_lip_y = 0.0
        self.is_speaking = False
        self.speech_start_time = 0
        self.speech_text = ""
        self.speech_phonemes = []
        self.current_phoneme_index = 0
        self.eye_movement_enabled = True
        self.eye_movement_range = 0.3
        # Sleep animation state
        self.sleep_animation_phase = 0.0
        self.is_sleeping = False
        # WAV playback state
        self.is_playing_wav = False
        self.wav_start_time = 0
        self.wav_duration = 0

avatar_state = AvatarState()

# --- OpenGL and Pygame Setup ---
def init_display():
    pygame.init()
    pygame.mixer.init()  # Initialize mixer for WAV playback
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Enhanced 2D Avatar - Press keys for emotions, ENTER to speak")
    glClearColor(0.1, 0.1, 0.2, 1.0)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluOrtho2D(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT)
    glMatrixMode(GL_MODELVIEW)

def load_texture(image_path):
    if not os.path.exists(image_path):
        print(f"FATAL ERROR: Texture not found '{image_path}'. Please check file paths.")
        pygame.quit()
        exit()
    try:
        img = Image.open(image_path).convert("RGBA")
    except Exception as e:
        print(f"Error loading texture '{image_path}': {e}")
        pygame.quit()
        exit()
    img_data = np.array(list(img.getdata()), np.uint8)
    texture_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, img.width, img.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
    return texture_id, img.width, img.height

def load_all_textures(path=PARTS_PATH):
    print("--- Loading Textures ---")
    textures = {}
    texture_info = {}
    
    # Load base face texture and get dimensions
    base_tex, base_w, base_h = load_texture(os.path.join(path, "base.png"))
    textures["base"] = base_tex
    texture_info["base"] = (base_w, base_h)
    
    # Load eye textures only (no mouth or eyebrow textures needed)
    texture_files = {
        "l_eye_bg": "left_eye_background_and_border.png",
        "r_eye_bg": "right_eye_background_and_border.png",
        "l_pupil": "left_eye_pupil.png",
        "r_pupil": "right_eye_pupil.png",
    }
    
    for key, filename in texture_files.items():
        tex_id, w, h = load_texture(os.path.join(path, filename))
        textures[key] = tex_id
        texture_info[key] = (w, h)
    
    print("All textures loaded successfully.")
    return textures, texture_info

# --- Mesh & Animation ---
def create_quad_mesh(cx, cy, width, height):
    x1, y1 = cx - width / 2, cy - height / 2
    x2, y2 = cx + width / 2, cy + height / 2
    vertices = np.array([(x1, y1), (x2, y1), (x2, y2), (x1, y2)], dtype=np.float32)
    tex_coords = np.array([(0, 1), (1, 1), (1, 0), (0, 0)], dtype=np.float32)
    return vertices, tex_coords

def create_curved_eyebrow_mesh(cx, cy, width, height, curve_strength=0.3):
    """Create a curved eyebrow mesh with natural human-like curvature"""
    segments = 10
    vertices = []
    
    # Create curved top and bottom edges
    for i in range(segments + 1):
        t = i / segments
        x = cx - width/2 + t * width
        
        # Natural eyebrow curve - higher in the middle, tapering at ends
        curve_y = math.sin(t * math.pi) * curve_strength * height
        
        # Top edge (more curved)
        top_y = cy + height/2 + curve_y
        # Bottom edge (less curved)
        bottom_y = cy - height/2 + curve_y * 0.3
        
        vertices.extend([(x, bottom_y), (x, top_y)])
    
    return np.array(vertices, dtype=np.float32)

def _cubic_bezier(p0, p1, p2, p3, t):
    u = 1 - t
    return (u**3)*p0 + 3*(u**2)*t*p1 + 3*u*(t**2)*p2 + (t**3)*p3

def create_curved_lip_mesh(cx, cy, width, height, is_upper=True, curve_amount=0.0, segments=32, thickness=0.5):
    """
    Filled lip mesh as a triangle-strip:
     - computes two Bézier curves (outer & inner)
     - interleaves them into a single triangle strip
    """
    # control pts in [0..1]x[0..1]
    if is_upper:
        # p0 (left corner), p1,p2 = bows, p3=right corner
        p0 = np.array([0.0, 0.0])
        p1 = np.array([0.25, 0.2 + curve_amount])
        p2 = np.array([0.75, 0.2 + curve_amount])
        p3 = np.array([1.0, 0.0])
    else:
        # lower lip U‑shape
        p0 = np.array([0.0, 0.1 - curve_amount])
        p1 = np.array([0.25, -0.2 - curve_amount])
        p2 = np.array([0.75, -0.2 - curve_amount])
        p3 = np.array([1.0, 0.1 - curve_amount])

    outer = []
    inner = []
    for i in range(segments + 1):
        t = i / segments
        x_norm, y_norm = _cubic_bezier(p0, p1, p2, p3, t)
        x_world = cx - width/2 + x_norm * width
        y_world = cy       + y_norm * height

        # offset inward for “thickness”
        dir_y = 1.0 if is_upper else -1.0
        offset = dir_y * thickness * height
        outer.append((x_world, y_world))
        inner.append((x_world, y_world - offset))

    # build triangle strip: O0, I0, O1, I1, O2, I2, ...
    verts = []
    for (xo, yo), (xi, yi) in zip(outer, inner):
        verts.extend([ (xo, yo), (xi, yi) ])
    return np.array(verts, dtype=np.float32)

def create_curved_lip_mesh_old(cx, cy, width, height, is_upper=True, curve_amount=0.0):
    """Create curved lip mesh with natural human-like shape"""
    segments = 16
    vertices = []
    
    for i in range(segments + 1):
        t = i / segments
        x = cx - width/2 + t * width
        
        if is_upper:
            # Upper lip - natural M shape with cupid's bow
            center_dip = abs(t - 0.5) * 2  # Creates dip in center
            cupids_bow = math.sin(t * math.pi) * 0.3 - center_dip * 0.2
            base_curve = math.sin(t * math.pi) * curve_amount * height
            
            top_y = cy + height/2 + cupids_bow * height + base_curve
            bottom_y = cy - height/2 + base_curve
        else:
            # Lower lip - fuller, rounded shape
            fullness = math.sin(t * math.pi) * 0.8  # Fuller in center
            base_curve = -math.sin(t * math.pi) * curve_amount * height
            
            top_y = cy + height/2 + base_curve
            bottom_y = cy - height/2 - fullness * height + base_curve
        
        vertices.extend([(x, bottom_y), (x, top_y)])
    
    return np.array(vertices, dtype=np.float32)

def draw_quad(vertices, tex_coords, texture_id):
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glEnableClientState(GL_VERTEX_ARRAY)
    glEnableClientState(GL_TEXTURE_COORD_ARRAY)
    glVertexPointer(2, GL_FLOAT, 0, vertices)
    glTexCoordPointer(2, GL_FLOAT, 0, tex_coords)
    glDrawArrays(GL_QUADS, 0, 4)
    glDisableClientState(GL_VERTEX_ARRAY)
    glDisableClientState(GL_TEXTURE_COORD_ARRAY)

def draw_curved_shape(vertices, color):
    """Draw curved shape using triangle strip"""
    glDisable(GL_TEXTURE_2D)
    glColor4f(*color)
    glEnableClientState(GL_VERTEX_ARRAY)
    glVertexPointer(2, GL_FLOAT, 0, vertices)
    glDrawArrays(GL_TRIANGLE_STRIP, 0, len(vertices))
    glDisableClientState(GL_VERTEX_ARRAY)
    glColor4f(1.0, 1.0, 1.0, 1.0)  # Reset color

def draw_colored_quad(vertices, color):
    """Draw a solid colored quad without texture"""
    glDisable(GL_TEXTURE_2D)
    glColor4f(*color)
    glEnableClientState(GL_VERTEX_ARRAY)
    glVertexPointer(2, GL_FLOAT, 0, vertices)
    glDrawArrays(GL_QUADS, 0, 4)
    glDisableClientState(GL_VERTEX_ARRAY)
    glColor4f(1.0, 1.0, 1.0, 1.0)  # Reset color

def draw_scaled_quad(vertices, tex_coords, texture_id, scale_x=1.0, scale_y=1.0):
    """Draw a quad with scaling applied"""
    glPushMatrix()
    
    # Calculate center point
    center_x = (vertices[0][0] + vertices[2][0]) / 2
    center_y = (vertices[0][1] + vertices[2][1]) / 2
    
    # Apply scaling around center
    glTranslatef(center_x, center_y, 0)
    glScalef(scale_x, scale_y, 1.0)
    glTranslatef(-center_x, -center_y, 0)
    
    draw_quad(vertices, tex_coords, texture_id)
    glPopMatrix()

def draw_cropped_quad(vertices, tex_coords, texture_id, crop_top=0.0, crop_bottom=0.0):
    """Draw a quad with texture cropping from top or bottom"""
    glPushMatrix()
    
    # Modify vertices for cropping
    cropped_vertices = np.copy(vertices)
    cropped_tex_coords = np.copy(tex_coords)
    
    height = vertices[2][1] - vertices[0][1]
    
    if crop_top > 0:
        # Crop from top
        crop_pixels = height * crop_top
        cropped_vertices[2][1] -= crop_pixels  # Top right
        cropped_vertices[3][1] -= crop_pixels  # Top left
        cropped_tex_coords[2][1] = crop_top    # Adjust texture coordinates
        cropped_tex_coords[3][1] = crop_top
    
    if crop_bottom > 0:
        # Crop from bottom
        crop_pixels = height * crop_bottom
        cropped_vertices[0][1] += crop_pixels  # Bottom left
        cropped_vertices[1][1] += crop_pixels  # Bottom right
        cropped_tex_coords[0][1] = 1.0 - crop_bottom  # Adjust texture coordinates
        cropped_tex_coords[1][1] = 1.0 - crop_bottom
    
    draw_quad(cropped_vertices, cropped_tex_coords, texture_id)
    glPopMatrix()

# --- WAV File Duration Helper ---
def get_wav_duration(wav_file_path):
    """Get duration of WAV file in seconds"""
    try:
        with contextlib.closing(wave.open(wav_file_path, 'r')) as f:
            frames = f.getnframes()
            rate = f.getframerate()
            duration = frames / float(rate)
            return duration
    except Exception as e:
        print(f"Error getting WAV duration: {e}")
        return 0.0

# --- Enhanced Speak Function with WAV Support ---
def speak_with_wav_and_emotion(wav_file_path=None, text="", emotion="neutral"):
    """
    Enhanced function to play WAV file with lip sync and emotion
    
    Args:
        wav_file_path (str): Path to WAV file to play (optional)
        text (str): Text for lip sync animation
        emotion (str): Emotion to display during speech
    """
    if not wav_file_path and not text:
        print("Either WAV file or text must be provided")
        return
    
    def run_speech():
        avatar_state.target_emotion = emotion
        avatar_state.is_speaking = True
        avatar_state.speech_start_time = time.time()
        avatar_state.speech_text = text if text else "Speech audio playing"
        avatar_state.speech_phonemes = text_to_phonemes(text if text else "speaking now")
        avatar_state.current_phoneme_index = 0
        
        if wav_file_path and os.path.exists(wav_file_path):
            # Play WAV file
            avatar_state.is_playing_wav = True
            avatar_state.wav_start_time = time.time()
            avatar_state.wav_duration = get_wav_duration(wav_file_path)
            
            try:
                pygame.mixer.music.load(wav_file_path)
                pygame.mixer.music.play()
                
                # Wait for WAV to finish
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                    
            except Exception as e:
                print(f"Error playing WAV file: {e}")
            
            avatar_state.is_playing_wav = False
        
        if text and engine:
            # Also use TTS if text is provided
            engine.say(text)
            engine.runAndWait()
        
        avatar_state.is_speaking = False
        avatar_state.mouth_open_ratio = 0.0
        avatar_state.upper_lip_y = 0.0
        avatar_state.lower_lip_y = 0.0
    
    threading.Thread(target=run_speech, daemon=True).start()

# --- Phoneme-based Lip Sync ---
def text_to_phonemes(text):
    """Enhanced phoneme approximation for better lip sync"""
    phonemes = []
    words = re.findall(r'\b\w+\b', text.lower())
    
    for word in words:
        for i, char in enumerate(word):
            if char in 'aeiou':
                if char in 'ae':
                    phonemes.append(('vowel_wide', 0.18))  # Wide mouth for A, E
                else:
                    phonemes.append(('vowel_round', 0.16))  # Round mouth for O, U, I
            elif char in 'bpmf':
                phonemes.append(('bilabial', 0.12))  # Lips together
            elif char in 'td':
                phonemes.append(('dental', 0.10))  # Tongue to teeth
            elif char in 'kg':
                phonemes.append(('velar', 0.08))  # Back of tongue
            elif char in 'sz':
                phonemes.append(('sibilant', 0.14))  # Hissing sounds
            else:
                phonemes.append(('consonant', 0.08))
        phonemes.append(('pause', 0.03))
    
    return phonemes

def speak_with_emotion(text, emotion="neutral"):
    """Original speak function with emotion and lip sync"""
    if not text: 
        return
    
    def run_tts():
        avatar_state.target_emotion = emotion
        avatar_state.is_speaking = True
        avatar_state.speech_start_time = time.time()
        avatar_state.speech_text = text
        avatar_state.speech_phonemes = text_to_phonemes(text)
        avatar_state.current_phoneme_index = 0
        
        #wait to speak
        
        avatar_state.is_speaking = False
        avatar_state.mouth_open_ratio = 0.0
        avatar_state.upper_lip_y = 0.0
        avatar_state.lower_lip_y = 0.0
    
    threading.Thread(target=run_tts, daemon=True).start()

def update_animations(dt):
    current_time = time.time()
    speed = dt * avatar_state.emotion_transition_speed
    
    # Get current emotion parameters
    emotion = EMOTIONS[avatar_state.target_emotion]
    
    # Update emotion targets
    avatar_state.target_eyebrow_y = emotion["eyebrow_y"]
    avatar_state.target_eyebrow_r = emotion["eyebrow_r"]
    avatar_state.target_mouth_curve = emotion["mouth_c"]
    avatar_state.target_eye_open_ratio = emotion["eye_o"]
    avatar_state.target_pupil_size = emotion["pupil_s"]
    avatar_state.eye_movement_range = emotion["eye_move_range"]
    
    # Smooth transitions
    avatar_state.eyebrow_y += (avatar_state.target_eyebrow_y - avatar_state.eyebrow_y) * speed
    avatar_state.eyebrow_r += (avatar_state.target_eyebrow_r - avatar_state.eyebrow_r) * speed
    avatar_state.mouth_curve += (avatar_state.target_mouth_curve - avatar_state.mouth_curve) * speed
    avatar_state.pupil_size += (avatar_state.target_pupil_size - avatar_state.pupil_size) * speed
    
    # Eye movement control
    avatar_state.eye_movement_enabled = not emotion.get("eye_steady", False)
    avatar_state.is_sleeping = (avatar_state.target_emotion == "sleep")
    
    # Enhanced pupil movement with emotion-based range
    if avatar_state.eye_movement_enabled and current_time > avatar_state.next_gaze_shift_time:
        movement_range = avatar_state.eye_movement_range
        avatar_state.target_pupil_pos = np.array([
            random.uniform(-movement_range, movement_range), 
            random.uniform(-movement_range * 0.7, movement_range * 0.7)
        ])
        avatar_state.next_gaze_shift_time = current_time + random.uniform(1.5, 4.0)
    elif not avatar_state.eye_movement_enabled:
        avatar_state.target_pupil_pos = np.array([0.0, 0.0])
    
    avatar_state.pupil_pos += (avatar_state.target_pupil_pos - avatar_state.pupil_pos) * dt * 3.0
    
    # Sleep animation
    if avatar_state.is_sleeping:
        avatar_state.sleep_animation_phase += dt * 2.0
        # Slow breathing-like movement for sleeping
        sleep_offset = math.sin(avatar_state.sleep_animation_phase) * 0.05
        avatar_state.pupil_pos[1] = sleep_offset
    
    # Enhanced blinking system
    if not avatar_state.is_blinking and current_time > avatar_state.next_blink_time:
        avatar_state.is_blinking = True
        avatar_state.blink_start_time = current_time
        # Adjust blink frequency based on emotion
        if avatar_state.is_sleeping:
            avatar_state.blink_duration = 2.0  # Very slow blinks when sleeping
        elif avatar_state.target_emotion in ["fear", "surprise"]:
            avatar_state.blink_duration = 0.08  # Faster blinks when alert
        else:
            avatar_state.blink_duration = 0.12
    
    if avatar_state.is_blinking:
        progress = (current_time - avatar_state.blink_start_time) / avatar_state.blink_duration
        if progress <= 1.0:
            if avatar_state.is_sleeping:
                # For sleep, keep eyes mostly closed
                avatar_state.eye_open_ratio = 0.3 + math.sin(progress * math.pi) * 0.1
            else:
                avatar_state.eye_open_ratio = 1.0 - math.sin(progress * math.pi) * 0.8
        else:
            avatar_state.is_blinking = False
            avatar_state.eye_open_ratio = avatar_state.target_eye_open_ratio
            if avatar_state.is_sleeping:
                avatar_state.next_blink_time = current_time + random.uniform(0.5, 2.0)
            else:
                avatar_state.next_blink_time = current_time + random.uniform(2, 6)
    else:
        avatar_state.eye_open_ratio += (avatar_state.target_eye_open_ratio - avatar_state.eye_open_ratio) * speed
    
    # Enhanced lip sync with proper timing
    if avatar_state.is_speaking and avatar_state.speech_phonemes:
        elapsed = current_time - avatar_state.speech_start_time
        
        # Calculate current phoneme with proper timing
        phoneme_time = 0
        current_phoneme = None
        phoneme_progress = 0
        
        for i, (phoneme_type, duration) in enumerate(avatar_state.speech_phonemes):
            if elapsed < phoneme_time + duration:
                current_phoneme = phoneme_type
                phoneme_progress = (elapsed - phoneme_time) / duration
                break
            phoneme_time += duration
        
        # Set lip positions based on phoneme with smooth transitions
        if current_phoneme == 'vowel_wide':
            target_upper = -0.4
            target_lower = 0.5
            avatar_state.mouth_open_ratio = 0.8
        elif current_phoneme == 'vowel_round':
            target_upper = -0.2
            target_lower = 0.3
            avatar_state.mouth_open_ratio = 0.6
        elif current_phoneme == 'bilabial':
            target_upper = 0.05
            target_lower = -0.05
            avatar_state.mouth_open_ratio = 0.0
        elif current_phoneme == 'dental':
            target_upper = -0.15
            target_lower = 0.25
            avatar_state.mouth_open_ratio = 0.4
        elif current_phoneme == 'sibilant':
            target_upper = -0.1
            target_lower = 0.15
            avatar_state.mouth_open_ratio = 0.3
        elif current_phoneme == 'consonant':
            target_upper = -0.1
            target_lower = 0.2
            avatar_state.mouth_open_ratio = 0.3
        else:  # pause
            target_upper = 0.0
            target_lower = 0.0
            avatar_state.mouth_open_ratio = 0.1
        
        # Smooth lip movement with enhanced speed
        lip_speed = dt * 12
        avatar_state.upper_lip_y += (target_upper - avatar_state.upper_lip_y) * lip_speed
        avatar_state.lower_lip_y += (target_lower - avatar_state.lower_lip_y) * lip_speed
        
        # Add natural variation based on phoneme progress
        variation = math.sin(phoneme_progress * math.pi * 2) * 0.03
        avatar_state.upper_lip_y += variation
        avatar_state.lower_lip_y -= variation
    else:
        # Return to neutral position smoothly
        avatar_state.mouth_open_ratio *= max(0, 1.0 - (dt * 4.0))
        avatar_state.upper_lip_y *= max(0, 1.0 - (dt * 5.0))
        avatar_state.lower_lip_y *= max(0, 1.0 - (dt * 5.0))

# --- Main Application ---
def main():
    init_display()
    textures, texture_info = load_all_textures()
    
    CENTER_X, CENTER_Y = WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2
    
    # Calculate face dimensions based on base texture aspect ratio
    base_w, base_h = texture_info["base"]
    aspect_ratio = base_w / base_h
    face_height = 500
    face_width = face_height * aspect_ratio
    
    # Create face mesh
    face_v, face_tc = create_quad_mesh(CENTER_X, CENTER_Y, face_width, face_height)
    
    # Improved eye positioning and sizing
    eye_y_offset = face_height * 0.08  # Slightly lower positioning
    eye_x_offset = face_width * 0.18   # Closer together
    eye_size = face_width * 0.28       # Larger eye size for better visibility
    
    # Eye backgrounds
    l_eye_v, l_eye_tc = create_quad_mesh(CENTER_X - eye_x_offset, CENTER_Y + eye_y_offset, eye_size, eye_size * 0.8)
    r_eye_v, r_eye_tc = create_quad_mesh(CENTER_X + eye_x_offset, CENTER_Y + eye_y_offset, eye_size, eye_size * 0.8)
    
    # Pupils - properly sized and positioned
    pupil_size = eye_size * 0.6  # Larger pupils for better visibility
    l_pupil_v, l_pupil_tc = create_quad_mesh(CENTER_X - eye_x_offset, CENTER_Y + eye_y_offset, pupil_size, pupil_size)
    r_pupil_v, r_pupil_tc = create_quad_mesh(CENTER_X + eye_x_offset, CENTER_Y + eye_y_offset, pupil_size, pupil_size)
    
    # Curved Eyebrows - positioned higher to avoid overlap with eyes
    brow_y_offset = face_height * 0.22  # Increased from 0.18 to avoid eye overlap
    brow_size = eye_size * 1.0  # Slightly smaller
    l_brow_v = create_curved_eyebrow_mesh(CENTER_X - eye_x_offset, CENTER_Y + brow_y_offset, brow_size, eye_size * 0.05)
    r_brow_v = create_curved_eyebrow_mesh(CENTER_X + eye_x_offset, CENTER_Y + brow_y_offset, brow_size, eye_size * 0.05)
    
    # Curved Mouth with separate upper and lower lips
    mouth_y_offset = face_height * 0.2
    mouth_width = face_width * 0.25
    mouth_height = face_width * 0.06
    
    # Create curved lip meshes
    upper_lip_base_v = create_curved_lip_mesh(CENTER_X, CENTER_Y - mouth_y_offset + mouth_height/4, 
                                             mouth_width, mouth_height/2, is_upper=True, curve_amount=0.0)
    lower_lip_base_v = create_curved_lip_mesh(CENTER_X, CENTER_Y - mouth_y_offset - mouth_height/4, 
                                             mouth_width, mouth_height/2, is_upper=False, curve_amount=0.0)
    
    PUPIL_MOVEMENT_RANGE = np.array([eye_size * 0.15, eye_size * 0.1])
    
    clock = pygame.time.Clock()
    emotion_keys = {
        pygame.K_1: "happy", pygame.K_2: "sad", pygame.K_3: "angry",
        pygame.K_4: "surprise", pygame.K_5: "fear", pygame.K_6: "disgust",
        pygame.K_7: "amusement", pygame.K_8: "frustration", pygame.K_9: "embarrassment",
        pygame.K_0: "neutral", pygame.K_l: "love", pygame.K_c: "confusion",
        pygame.K_s: "sleep"
    }
    
    demo_phrases = [
        ("Hello! How are you today?", "happy"),
        ("I'm feeling a bit sad right now.", "sad"),
        ("This is really making me angry!", "angry"),
        ("Wow! That's absolutely amazing!", "surprise"),
        ("I'm so scared of what might happen.", "fear"),
        ("That's absolutely disgusting!", "disgust"),
        ("Haha, that's really funny!", "amusement"),
        ("This is so frustrating to deal with.", "frustration"),
        ("Oh no, I'm so embarrassed!", "embarrassment"),
        ("I love spending time with you.", "love"),
        ("I'm really confused about this.", "confusion"),
        ("I'm getting sleepy now...", "sleep")
    ]
    current_demo = 0
    
    running = True
    print("--- Controls ---")
    print("Keys 0-9, L, C, S: Change emotions (S = sleep)")
    print("ENTER: Speak demo phrase with emotion")
    print("SPACE: Cycle through demo phrases")
    print("W: Test WAV playback (requires 'test.wav' file)")
    
    while running:
        dt = clock.tick(30) / 1000.0
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: 
                running = False
            
            if event.type == pygame.KEYDOWN:
                if event.key in emotion_keys:
                    avatar_state.target_emotion = emotion_keys[event.key]
                    print(f"Emotion changed to: {emotion_keys[event.key]}")
                
                elif event.key == pygame.K_RETURN:
                    phrase, emotion = demo_phrases[current_demo]
                    speak_with_emotion(phrase, emotion)
                    print(f"Speaking: '{phrase}' with emotion: {emotion}")
                
                elif event.key == pygame.K_SPACE:
                    current_demo = (current_demo + 1) % len(demo_phrases)
                    phrase, emotion = demo_phrases[current_demo]
                    print(f"Next demo: '{phrase}' ({emotion})")
                
                elif event.key == pygame.K_w:
                    # Test WAV playback - requires a 'test.wav' file
                    test_wav = "test.wav"
                    if os.path.exists(test_wav):
                        speak_with_wav_and_emotion(
                            wav_file_path=test_wav,
                            text="Playing audio file with lip sync",
                            emotion="happy"
                        )
                        print(f"Playing WAV file: {test_wav}")
                    else:
                        print("test.wav file not found. Place a WAV file named 'test.wav' in the same directory.")

        update_animations(dt)
        glClear(GL_COLOR_BUFFER_BIT)
        glLoadIdentity()

        # --- Render Avatar ---
        # 1. Base Face
        draw_quad(face_v, face_tc, textures["base"])
        
        # 2. Eye Backgrounds with blink scaling
        eye_scale_y = avatar_state.eye_open_ratio
        draw_scaled_quad(l_eye_v, l_eye_tc, textures["l_eye_bg"], 1.0, eye_scale_y)
        draw_scaled_quad(r_eye_v, r_eye_tc, textures["r_eye_bg"], 1.0, eye_scale_y)

        # 3. Pupils with enhanced sleep mode cropping
        pupil_offset = avatar_state.pupil_pos * PUPIL_MOVEMENT_RANGE
        pupil_scale = avatar_state.pupil_size
        
        # Enhanced sleep state - crop from top to show only bottom part
        if avatar_state.is_sleeping:
            # Calculate crop amount based on eye openness
            crop_top_amount = max(0.0, 1.0 - avatar_state.eye_open_ratio * 0.8)  # Crop more when eyes are more closed
            pupil_offset_y = pupil_offset[1] + eye_size * 0.22  # Move down slightly
            
            # Left pupil with top cropping
            glPushMatrix()
            glTranslatef(pupil_offset[0], pupil_offset_y, 0)
            draw_cropped_quad(l_pupil_v, l_pupil_tc, textures["l_pupil"], crop_top=crop_top_amount)
            glPopMatrix()
            
            # Right pupil with top cropping
            glPushMatrix()
            glTranslatef(pupil_offset[0], pupil_offset_y, 0)
            draw_cropped_quad(r_pupil_v, r_pupil_tc, textures["r_pupil"], crop_top=crop_top_amount)
            glPopMatrix()
        else:
            # Normal pupil rendering with scaling
            pupil_scale_y = pupil_scale * eye_scale_y
            
            # Left pupil
            glPushMatrix()
            glTranslatef(pupil_offset[0], pupil_offset[1], 0)
            draw_scaled_quad(l_pupil_v, l_pupil_tc, textures["l_pupil"], pupil_scale, pupil_scale_y)
            glPopMatrix()
            
            # Right pupil
            glPushMatrix()
            glTranslatef(pupil_offset[0], pupil_offset[1], 0)
            draw_scaled_quad(r_pupil_v, r_pupil_tc, textures["r_pupil"], pupil_scale, pupil_scale_y)
            glPopMatrix()

        # 4. Curved Eyebrows with solid color and enhanced animation
        y_offset = avatar_state.eyebrow_y * face_height
        rotation = avatar_state.eyebrow_r
        
        for brow_v, rot_dir in [(l_brow_v, 1), (r_brow_v, -1)]:
            glPushMatrix()
            # Calculate center of eyebrow for rotation
            center_x = np.mean(brow_v[::2, 0])  # Average of x coordinates
            center_y = np.mean(brow_v[::2, 1]) + y_offset  # Average of y coordinates with offset
            
            glTranslatef(center_x, center_y, 0)
            glRotatef(rotation * rot_dir, 0, 0, 1)
            glTranslatef(-center_x, -center_y + y_offset, 0)
            
            # Adjust eyebrow vertices for offset
            adjusted_brow_v = np.copy(brow_v)
            adjusted_brow_v[:, 1] += y_offset
            
            draw_curved_shape(adjusted_brow_v, LIP_EYEBROW_COLOR_GL)
            glPopMatrix()

        # 5. Enhanced Curved Mouth with natural lip movement
        curve_amount = avatar_state.mouth_curve
        
        # Upper lip with enhanced curvature and movement
        upper_lip_v = create_curved_lip_mesh(
            CENTER_X, 
            CENTER_Y - mouth_y_offset + mouth_height/4 + avatar_state.upper_lip_y * mouth_height, 
            mouth_width, 
            mouth_height/2, 
            is_upper=True, 
            curve_amount=curve_amount
        )
        draw_curved_shape(upper_lip_v, LIP_EYEBROW_COLOR_GL)
        
        # Lower lip with enhanced curvature and movement
        lower_lip_v = create_curved_lip_mesh(
            CENTER_X, 
            CENTER_Y - mouth_y_offset - mouth_height/4 + avatar_state.lower_lip_y * mouth_height, 
            mouth_width, 
            mouth_height/2, 
            is_upper=False, 
            curve_amount=curve_amount
        )
        draw_curved_shape(lower_lip_v, LIP_EYEBROW_COLOR_GL)

        pygame.display.flip()
    
    pygame.quit()

if __name__ == '__main__':
    main()