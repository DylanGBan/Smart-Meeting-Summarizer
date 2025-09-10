from openai import OpenAI
from dotenv import load_dotenv
from moviepy import AudioFileClip
import os
import sys
import logging

load_dotenv()

OPEN_AI_KEY = os.getenv("OPEN_AI_KEY")
client = OpenAI(api_key=OPEN_AI_KEY)

def file_extraction(file_path):
    logger = logging.getLogger(__name__)
    logging.basicConfig(filename='debug.log', encoding='utf-8', level=logging.DEBUG)

    if type(file_path) is not str:
        logger.warning('Invalid paramter input')
        return -1

    try:

        file_name = os.path.basename(file_path).split(".mp3")[0]

        with AudioFileClip(file_path) as audio_file:
            duration = audio_file.duration

            if duration > 1440:
                full_transcription = []

                ten_min_passes = round(round(duration / 60, 1) / 10, 0)
                start_min = 0
                end_min = 0

                print(int(ten_min_passes))

                for i in range(int(ten_min_passes)):
                    print("in")
                    end_min += 10 
                    clip_10_min = audio_file.subclipped(start_min * 60, end_min * 60)
                    clip_10_min_fname = file_name + "_10.mp3"
                    clip_10_min.write_audiofile(clip_10_min_fname)

                    clipped_audio_file = open(clip_10_min_fname, "rb")

                    transcription = client.audio.transcriptions.create(
                    model="gpt-4o-transcribe", 
                    file=clipped_audio_file, 
                    response_format="text"
                    )

                    full_transcription.append(transcription)
                    start_min = end_min

                if end_min * 60 < duration:
                    clip = audio_file.subclipped(end_min * 60)
                    clip.write_audiofile(file_name + "_final.mp3")

                    clipped_audio_file = open(file_name + "_final.mp3", "rb")

                    transcription = client.audio.transcriptions.create(
                    model="gpt-4o-transcribe", 
                    file=clipped_audio_file, 
                    response_format="text"
                    )

                    full_transcription.append(transcription)
                
                return full_transcription
            
            else:
                audio_file = open(file_path, "rb")

                transcription = client.audio.transcriptions.create(
                model="gpt-4o-transcribe", 
                file=audio_file, 
                response_format="text"
                )

                return transcription

    
    except Exception as e:
        logger.warning(f'Exception: {e}')
        return -1
    
