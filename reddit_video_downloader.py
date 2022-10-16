import json
import os

os.system('cls')
from requests import get, exceptions
from sys import argv as command_line_args

debug_url: str = ''
overwrite: bool = True


def get_user_agent():
    # some fake one I found :/
    return 'Mozilla/5.0 (iPad; U; CPU OS 3_2_1 like Mac OS X; en-us) AppleWebKit/531.21.10 (KHTML, like Gecko) Mobile/7B405'


def say(text, type=''):
    if type == 'error':
        prefix = '\n[!] '
    else:
        prefix = '[>] '
    print(prefix + text)


def get_video(url):
    try:  # checks if link is valid
        r = get(
            url + '.json',
            headers={'User-agent': get_user_agent()}
        )
    except exceptions.MissingSchema:
        say('Please provide a valid URL', 'error')
        quit()

    if 'error' in r.text:
        if r.status_code == 404:
            say('Post not found', 'error')

        quit()

    try:
        json_data = json.loads(r.text)[0]['data']['children'][0]['data']
        say('Post Found!')
        say(f'Title: {json_data["title"]}')
        say(f'In sub-reddit: {json_data["subreddit_name_prefixed"]}')
        say(f'Posted by: {json_data["author"]}')
    except json.decoder.JSONDecodeError:
        say('Post not found', 'error')
        quit()

    try:  # checks if post contains video
        video_url = json_data['secure_media']['reddit_video']['fallback_url']
        say(f'Video URL: {video_url}')
        r = get(video_url).content
        with open('download.mp4', 'wb') as file:
            file.write(r)
        get_audio(json_data)
        stitch_video(json_data)
    except TypeError:
        say('Only posts with videos are supported', 'error')


def get_audio(json_data):
    try:
        audio_url = json_data['secure_media']['reddit_video']['hls_url'].split('HLS')[0]
        audio_url += 'HLS_AUDIO_160_K.aac'
        r = get(audio_url).content
        with open('audio.aac', 'wb') as file:
            file.write(r)
    except TypeError:
        say('No audio found.', 'error')


def cleanup_filename(f: str) -> str:
    """ Strips characters that break ffmpeg in a filename, and also removes duplicate spaces.

    Args:
        f (str): The filename to be adjusted. (no extension)

    Returns:
        str: The filename stripped of any problematic characters and formatted neatly.
    """
    return f.replace('any %', '').replace('%', '') \
               .replace(' | ', '').replace('|', '') \
               .replace(':', '-').replace('#', '').replace('@', '') \
               .replace('   ', ' ').replace('  ', ' ') \
           + '.mp4'


def stitch_video(json_data):
    """ Runs ffmpeg and downloads the video.
    """
    global overwrite
    filename: str = cleanup_filename(str(json_data["title"]))
    filename: str = 'A:/' + filename
    file_already_exists: bool = os.path.exists(filename)

    if file_already_exists and not overwrite:
        say('Aborted (File already exists)')
        return

    if overwrite:
        overwrite_cmd: str = '-y'
    elif not overwrite:
        overwrite_cmd: str = '-n'
    else:
        overwrite_cmd: str = ''  # Prompt for input

    # TODO. Make path a variable so user can change the download location.
    c: str = 'ffmpeg ' + overwrite_cmd + \
             ' -loglevel quiet -i download.mp4 -i audio.aac -map 0 -map 1:a -c:v copy -shortest ' \
             '\"' + filename + '\"'
    os.system('@' + c)  # Run the ffmpeg cmd
    if os.path.exists(filename):
        if file_already_exists and overwrite:
            say('Complete! (Overwritten)')
        else:
            say('Complete!')
    else:
        say('Something went wrong and the file could not be saved.')


def help_page():
    print(f"""
        Usage : {os.path.basename(command_line_args[0])} <URL_TO_POST_WITH_VIDEO>
    """)


if debug_url:
    get_video(debug_url)
else:
    num_of_args = len(command_line_args)
    if num_of_args in [0, 1]:
        help_page()
    else:
        get_video(command_line_args[1])
