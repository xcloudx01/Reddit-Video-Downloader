import json
import os
import re
import random
import string
import time
import webbrowser
import urllib.request as req
from requests import get, exceptions
from sys import argv as command_line_args
os.system('cls')

download_dir: str = 'A:/'
overwrite: bool = True
debug: bool = False
debug_url: str = ''  # Put a URL here to always download it.
touch_file: bool = True


def get_user_agent():
    # some fake one I found :/
    return 'Mozilla/5.0 (iPad; U; CPU OS 3_2_1 like Mac OS X; en-us) ' \
           'AppleWebKit/531.21.10 (KHTML, like Gecko) Mobile/7B405'


def colored(r, g, b, text):
    return "\033[38;2;{};{};{}m{} \033[38;2;255;255;255m".format(r, g, b, text)


def print_lines():
    print(('-' * 30) + '\n')


def say(text, msg_type=''):
    if msg_type == 'error':
        print(colored(255, 0, 0, '*Error*'))
        print(text)
        print_lines()
    elif msg_type == 'success':
        print(colored(0, 255, 0, text))
        print_lines()
    else:
        prefix = '[>] '
        print(prefix + text)


def get_gif(json_data):
    try:
        gif_name = cleanup_filename(json_data["title"]) + '.gif'
        gif_url = json_data['url_overridden_by_dest']
        dl_path = download_dir + gif_name
        req.urlretrieve(gif_url, dl_path)
        for i in range(0, 15):
            if i >= 15:
                say('Timed out waiting for the download of: ' + gif_name, 'error')
                return
            elif not os.path.exists(dl_path):
                time.sleep(0.5)
            else:
                say('Successfully downloaded: ' + gif_name, 'success')
                return


    except TypeError:
        say('Could not download the gif', 'error')


def get_video(source_url):
    if not re.match(r'http?s://.+/r/.+/comments/', source_url):
        say('Provided URL is not from Reddit.', 'error')
        if debug:
            say(re.match(r'http?s://.+/r/.+/comments/', source_url))
            say('Source_Url is:' + source_url)
        return
    # TODO Need to strip away from the URL or it won't work: ?context=3
    try:  # checks if link is valid
        r = get(
            source_url + '.json',
            headers={'User-agent': get_user_agent()}
        )
    except exceptions.MissingSchema:
        say('Please provide a valid URL', 'error')
        return

    if 'error' in r.text:
        if r.status_code == 404:
            say('Post not found', 'error')
            say('Try removing anything after the first "?" in the URL')
            return

    try:
        json_data = json.loads(r.text)[0]['data']['children'][0]['data']
        if debug:
            say('Post Found!')  # I feel this is too verbose when not debugging.
            say(f'Title: {json_data["title"]}')
            say(f'In sub-reddit: {json_data["subreddit_name_prefixed"]}')
            say(f'Posted by: {json_data["author"]}')
    except json.decoder.JSONDecodeError:
        say('Post not found', 'error')
        return

    try:  # checks if post contains video
        video_url = json_data['secure_media']['reddit_video']['fallback_url']
        if debug:
            say(f'Video URL: {video_url}')
        say('Please wait, downloading video.. (No progress is shown)')
        r = get(video_url).content
        with open('download.mp4', 'wb') as file:
            file.write(r)
        get_audio(json_data)
        stitch_video(json_data)
    except TypeError:
        try:
            get_gif(json_data)  # Post isn't a video. Try Gif downloader instead.
        except TypeError:
            say('Something went wrong and both .mp4 and .gif downloads failed.', 'error')
            if debug:
                say('breakpoint reached')


def get_audio(json_data):
    try:
        audio_url = json_data['secure_media']['reddit_video']['hls_url'].split('HLS')[0]
        audio_url += 'HLS_AUDIO_160_K.aac'
        r = get(audio_url).content
        with open('audio.aac', 'wb') as file:
            file.write(r)
    except TypeError:
        say('No audio found.', 'error')


def alphanumeric_str(length):
    return ''.join((random.choice(string.hexdigits) for _ in range(length)))


def demojify(text):
    reg = re.compile("["
                     u"\U0001F600-\U0001F64F"  # emoticons
                     u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                     u"\U0001F680-\U0001F6FF"  # transport & map symbols
                     u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                     u"\U00002500-\U00002BEF"  # chinese char
                     u"\U00002702-\U000027B0"
                     u"\U00002702-\U000027B0"
                     u"\U000024C2-\U0001F251"
                     u"\U0001f926-\U0001f937"
                     u"\U00010000-\U0010ffff"
                     u"\u2640-\u2642" 
                     u"\u2600-\u2B55"
                     u"\u200d"
                     u"\u23cf"
                     u"\u23e9"
                     u"\u231a"
                     u"\ufe0f"  # dingbats
                     u"\u3030"
                     "]+", re.UNICODE)
    return re.sub(reg, '', text)


def cleanup_filename(filename: str) -> str:
    """ Strips characters that break ffmpeg in a filename, and also removes duplicate spaces.

    Args:
        filename (str): The filename to be adjusted. (no extension)

    Returns:
        str: The filename stripped of any problematic characters and formatted neatly.
    """
    filename = demojify(filename)  # Emojis in filenames raises an exception in request.py:249
    clean_filename = filename.replace('any %', '').replace('%', '').replace("?", '') \
                             .replace(' | ', '').replace('|', '') \
                             .replace(':', '-').replace('#', '').replace('@', '') \
                             .strip()
    if clean_filename == '':  # Discord can't send videos titled '.' (support for /r/shitposting)
        clean_filename = 'Reddit-' + alphanumeric_str(5)
    return clean_filename


def stitch_video(json_data):
    """ Runs ffmpeg and downloads the video.
    """
    global overwrite
    filename: str = cleanup_filename(str(json_data["title"])) + '.mp4'
    filename: str = download_dir + filename
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

    c: str = 'ffmpeg ' + overwrite_cmd + \
             ' -loglevel quiet -i download.mp4 -i audio.aac -map 0 -map 1:a -c:v copy -shortest ' \
             '\"' + filename + '\"'
    os.system('@' + c)  # Run the ffmpeg cmd
    if os.path.exists(filename):
        if touch_file:
           webbrowser.open(download_dir)
        if file_already_exists and overwrite:
            say('Complete! (Overwritten)', 'success')
        else:
            say('Complete!', 'success')

    else:
        say('Something went wrong and the file could not be saved.', 'error')


def help_page():
    print(f"""
        Usage : {os.path.basename(command_line_args[0])} <URL_TO_POST_WITH_VIDEO>
    """)


def assert_tests():
    assert download_dir[-1] == '/', 'download_dir MUST end in slash'


# MAIN CODE
assert_tests()  # Must run assertion tests before continuing.
if debug_url:
    get_video(debug_url)
else:
    while True is True:  # Inf loop so that it's easier to download another video. Due to prompt being active again.
        url = input("Please input Reddit URL: ")
        if url != '':
            get_video(url)
