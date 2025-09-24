from typing import Dict
import urllib.parse
import requests
import json
import os
import subprocess
import time


class ControllerError(Exception):
    """ A custom type that is raised by the Spotify Controller """
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class Artist:
    def __init__(self, spotify_artist_or_show_object: dict) -> None:
        if spotify_artist_or_show_object is None:
            raise ValueError("`Artist` class requires a `SimplifiedArtistObject` from spotify")

        if "name" not in spotify_artist_or_show_object:
            raise KeyError(f"No field `name` found in artist object: `{spotify_artist_or_show_object}`")
        if "external_urls" not in spotify_artist_or_show_object:
            raise KeyError(f"No field `external_urls` found in artist object: `{spotify_artist_or_show_object}`")
        if "spotify" not in spotify_artist_or_show_object["external_urls"]:
            raise KeyError(f"No field `spotify` found in artist object['external_urls']: `{spotify_artist_or_show_object}`")

        self.name = spotify_artist_or_show_object["name"]
        self.url = spotify_artist_or_show_object["external_urls"]["spotify"]
    
    def get_str(self) -> str:
        if self.url:
            return f"[{self.name}]({self.url})"
        return self.name


class Track:
    def __init__(self, spotify_track_or_episode_object: dict) -> None:
        if spotify_track_or_episode_object is None:
            raise ValueError("`Track` class requires a `TrackObject` or an `EpisodeObject` from spotify")

        if "type" not in spotify_track_or_episode_object:
            raise KeyError(f"No field `type` found in track/episode object `{spotify_track_or_episode_object}`")
        self.track_type = spotify_track_or_episode_object["type"]

        if "name" not in spotify_track_or_episode_object:
            raise KeyError(f"No field `name` found in {self.track_type} object `{spotify_track_or_episode_object}`")
        if "external_urls" not in spotify_track_or_episode_object:
            raise KeyError(f"No field `external_urls` found in {self.track_type} object `{spotify_track_or_episode_object}`")
        if "spotify" not in spotify_track_or_episode_object["external_urls"]:
            raise KeyError(f"No field `spotify` found in {self.track_type} object['external_urls'] `{spotify_track_or_episode_object}`")
        if "duration_ms" not in spotify_track_or_episode_object:
            raise KeyError(f"No field `duration_ms` found in {self.track_type} object `{spotify_track_or_episode_object}`")
        
        if self.track_type == "track":
            if "album" not in spotify_track_or_episode_object:
                raise KeyError(f"No field `album` found in {self.track_type} object `{spotify_track_or_episode_object}`")
            if "images" not in spotify_track_or_episode_object["album"]:
                raise KeyError(f"No field `images` found in {self.track_type} object['album'] `{spotify_track_or_episode_object}`")
            if "artists" not in spotify_track_or_episode_object:
                raise KeyError(f"No field `artists` found in {self.track_type} object `{spotify_track_or_episode_object}`")

            self.artists = []
            for artist in spotify_track_or_episode_object["artists"]:
                self.artists.append(Artist(artist))
            self.image = spotify_track_or_episode_object["album"]["images"][0]["url"]
        elif self.track_type == "episode":
            if "images" not in spotify_track_or_episode_object:
                raise KeyError(f"No field `images` found in {self.track_type} object `{spotify_track_or_episode_object}`")
            if "show" not in spotify_track_or_episode_object:
                raise KeyError(f"No field `show` found in {self.track_type} object `{spotify_track_or_episode_object}`")

            self.artists = [Artist(spotify_track_or_episode_object["show"]),]
            self.image = spotify_track_or_episode_object["images"][0]["url"]
        else:
            raise TypeError("`Track` class received unexpected type from Spotify. Must be one of `TrackObject` or `EpisodeObject`")

        self.name = spotify_track_or_episode_object["name"]
        self.url = spotify_track_or_episode_object["external_urls"]["spotify"]
        self.duration_ms = spotify_track_or_episode_object["duration_ms"]

    def humanize_duration(self) -> str:
        """
        Converts a duration given in seconds to a human-readable format (e.g., "1 hour 30 minutes").

        Parameters:
        - seconds (int): The duration in seconds to be converted.

        Returns:
        - str: The human-readable format of the duration.
        """
        MILLIS = 1
        SECONDS = 1000 * MILLIS
        MINUTES = 60 * SECONDS
        HOURS = 60 * MINUTES

        millis = self.duration_ms
        hours = millis // HOURS
        millis = millis % HOURS
        minutes = millis // MINUTES
        millis = millis % MINUTES
        seconds = millis // SECONDS

        human_duration = ""
        if hours > 1:
            human_duration += f"{hours} hours "
        elif hours == 1:
            human_duration += "1 hour "

        if minutes > 1:
            human_duration += f"{minutes} minutes "
        elif minutes == 1:
            human_duration += "1 minute "

        if seconds > 1:
            human_duration += f"{seconds} seconds"
        elif seconds == 1:
            human_duration += "1 second"

        return human_duration

    def get_str(self):
        return f"**{self.name}** [{self.humanize_duration()}] by {self.artists[0].get_str()}"


librespot = None
SPOTIFY_API_PREFIX="https://api.spotify.com/v1"


def is_valid_token(token: str) -> bool:
    response = requests.get(f"{SPOTIFY_API_PREFIX}/tracks/2TpxZ7JUBn3uw46aR7qd6V", headers={
        "Authorization": f"Bearer {token}"
    })
    if 300 > response.status_code >= 200:
        return True 
    elif response.status_code == 401:
        return False
    raise ValueError(f"is_valid_token received unexpected response from Spotify: code {response.status_code} and text {response.text}")


def logout() -> bool: 
    """
    "Logs out" the user by removing all references to access tokens or refresh tokens both locally 
    as well as on the auth server

    :returns: `True` if the user was logged out on the auth server. `False` if the user 
    was not logged out on the auth server. This is probably because the user is already 
    logged out
    """

    if os.getenv("SPOTIFY_ACCESS_TOKEN"):
        del os.environ["SPOTIFY_ACCESS_TOKEN"] 

    if os.getenv("SPOTIFY_REFRESH_TOKEN"):
        del os.environ["SPOTIFY_REFRESH_TOKEN"]

    response = requests.delete(f"{os.getenv('AUTH_SERVER')}/access-token/{os.getenv('AUTH_SERVER_SECURITY')}")
    if 300 > response.status_code >= 200:
        print("Successfully logged out")
        return True 

    print("Attempted logout failed with 404. User is likely already logged out")
    return False 


def refresh_token(refresh_token: str) -> Dict[str, str] | None: 
    response = requests.post(f"{os.getenv('AUTH_SERVER')}/refresh-token?state={os.getenv('AUTH_SERVER_SECURITY')}&refresh_token={refresh_token}")
    if 300 > response.status_code >= 200:
        body = json.loads(response.text)
        return body

    print(f"refresh_token failed with code {response.status_code} and text {response.text}")
    return None


def get_spotify_headers(): 
    return {
        "Authorization": f"Bearer {get_access_token()['access_token']}",
    }


def get_access_token() -> Dict[str, str] | None:
    response = requests.get(f"{os.getenv('AUTH_SERVER')}/access-token/{os.getenv('AUTH_SERVER_SECURITY')}")
    if 300 > response.status_code >= 200:
        return json.loads(response.text)
    return refresh_token(os.getenv("SPOTIFY_REFRESH_TOKEN"))


def is_playing():
    response = requests.get(f"{SPOTIFY_API_PREFIX}/me/player", headers=get_spotify_headers())
    if 300 > response.status_code >= 200: 
        body = json.loads(response.text)
        return body["is_playing"]
    
    print(f"is_playing failed with status {response.status_code} and text {response.text}")


def get_now_playing() -> Track: 
    response = requests.get(f"{SPOTIFY_API_PREFIX}/me/player/queue", headers=get_spotify_headers())
    if response.status_code == 200:
        body = json.loads(response.text)
        try: 
            return Track(body["currently_playing"])
        except Exception as e: 
            raise ControllerError(f"get_now_playing failed to create track info due to `{e}`")

    raise ControllerError(f"get_now_playing failed with status {response.status_code} and text `{response.text}`")


def get_queue(): 
    response = requests.get(f"{SPOTIFY_API_PREFIX}/me/player/queue", headers=get_spotify_headers())
    if response.status_code != 200:
        raise ControllerError(f"get_queue failed with status {response.status_code} and text `{response.text}`")

    body = json.loads(response.text)
    queue = []
    for track in body["queue"]:
        try: 
            queue.append(Track(track))
        except Exception as e:
            raise ControllerError(f"get_queue failed to create track info due to `{e}`")

    return queue


def play():
    response = requests.put(f"{SPOTIFY_API_PREFIX}/me/player/play?device_id={get_bot_device_id()}", headers=get_spotify_headers())
    if 300 > response.status_code >= 200:
        print("Resuming playback")
    else:
        print(f"Failed to resume playback with status {response.status_code} and text {response.text}")


def pause():
    response = requests.put(f"{SPOTIFY_API_PREFIX}/me/player/pause?device_id={get_bot_device_id()}", headers=get_spotify_headers())
    if 300 > response.status_code >= 200:
        print("Pausing playback")
    else:
        print(f"Failed to pause playback with status {response.status_code} and text {response.text}")


def skip(dir: str):
    """
    :param dir: Either 'next' or 'previous'
    """
    if dir not in ("next", "previous"):
        raise ValueError("dir must either be 'next' or 'previous'")
        
    response = requests.post(f"{SPOTIFY_API_PREFIX}/me/player/{dir}?device_id={get_bot_device_id()}", headers=get_spotify_headers())
    if 300 > response.status_code >= 200:
        print(f"Skipping to {dir}")
    else:
        print(f"Failed to skip with status {response.status_code} and text {response.text}")


def search(query: str):
    encoded_query = urllib.parse.quote_plus(query)
    response = requests.get(f"{SPOTIFY_API_PREFIX}/search?q={encoded_query}&type=track&limit=1", headers=get_spotify_headers())
    if response.status_code == 200:
        return json.loads(response.text)
    else: 
        print(response.status_code)
        print(response.text)


def add_to_queue(uri: str): 
    encoded_uri = urllib.parse.quote(uri)
    response = requests.post(f"{SPOTIFY_API_PREFIX}/me/player/queue?uri={encoded_uri}&device_id={get_bot_device_id()}", headers=get_spotify_headers())
    if 300 > response.status_code >= 200:
        return response
    else:
        print(f"add_to_queue failed with response {response.status_code} and text {response.text}")


def get_bot_device_id(): 
    response = requests.get(f"{SPOTIFY_API_PREFIX}/me/player/devices", headers=get_spotify_headers())
    if 300 > response.status_code >= 200:
        body = json.loads(response.text)
        for device in body["devices"]: 
            if device["name"] == os.getenv("BOT_NAME"): 
                print(f"found device {device['id']}")
                return device["id"]
        print("get_bot_device_id failed to find a device")
    else:
        print(f"get_bot_device_id failed with response {response.status_code} and text {response.text}")

    return None


def switch_to_device():
    bot_device_id = get_bot_device_id()
    headers = get_spotify_headers()
    response = requests.get(f"{SPOTIFY_API_PREFIX}/me/player/devices", headers=headers)
    if 300 > response.status_code >= 200:
        body = json.loads(response.text)
        for device in body["devices"]:
            if device["is_active"] and device["id"] == bot_device_id:
                print("Bot is already the active device")
                return

    headers["Content-Type"] = "application/json"
    response = requests.put(f"{SPOTIFY_API_PREFIX}/me/player", headers=headers, json={
        "device_ids": [
            bot_device_id,
        ],
        "play": True
    })
    if 300 > response.status_code >= 200 :
        print("Successfully transferred playback")
    else:
        print(f"switch_to_device failed with code {response.status_code} and text {response.text}")


def set_volume_percent(percent: int): 
    if percent < 0 or percent > 100:
        raise ValueError("percent must be between 0 and 100 inclusive")
    response = requests.put(f"{SPOTIFY_API_PREFIX}/me/player/volume?volume_percent={percent}", headers=get_spotify_headers())
    if 300 > response.status_code >= 200:
        print("Successfully set the volume")
    else:
        print(f"set_volume_percent failed with status {response.status_code} and message {response.text}")


def start_librespot():
    global librespot 
    print(get_access_token())
    librespot = subprocess.Popen([
        "librespot",
        "--name", os.getenv("BOT_NAME"),
        "--backend", "pipe",
        "--bitrate", "320",
        "--access-token", get_access_token()["access_token"],
        "--enable-volume-normalisation",
        "--initial-volume", "100",
    ], stdout=subprocess.PIPE)


def stop_librespot():
    global librespot 
    if librespot:
        librespot.terminate()
        librespot = None


def _refresh_librespot():
    global librespot 
    print(f"starting refresh thread: Librespot is '{librespot}'")
    if librespot:
        print("Waiting to refresh librespot in 1 hour")
        time.sleep(3590)
        print("Refreshing librespot")
        stop_librespot()
        start_librespot()
