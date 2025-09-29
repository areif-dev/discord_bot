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
    def __init__(self, spotify_object: dict) -> None:
        if spotify_object is None:
            raise ValueError("`Artist` class requires a `SimplifiedArtistObject` from spotify")

        if "type" not in spotify_object:
            raise KeyError(f"`Artist` missing required 'type' key in spotify object `{spotify_object}`")

        if spotify_object["type"] in ("show", "artist"):
            if "name" not in spotify_object:
                raise KeyError(f"No field `name` found in artist object: `{spotify_object}`")
            if "external_urls" not in spotify_object:
                raise KeyError(f"No field `external_urls` found in artist object: `{spotify_object}`")
            if "spotify" not in spotify_object["external_urls"]:
                raise KeyError(f"No field `spotify` found in artist object['external_urls']: `{spotify_object}`")

            self.name = spotify_object["name"]
            self.url = spotify_object["external_urls"]["spotify"]

        elif spotify_object["type"] == "user":
            if "display_name" not in spotify_object:
                raise KeyError(f"No field `display_name` found in artist object: `{spotify_object}`")
            if "external_urls" not in spotify_object:
                raise KeyError(f"No field `external_urls` found in artist object: `{spotify_object}`")
            if "spotify" not in spotify_object["external_urls"]:
                raise KeyError(f"No field `spotify` found in artist object['external_urls']: `{spotify_object}`")

            self.name = spotify_object["display_name"]
            self.url = spotify_object["external_urls"]["spotify"]

        elif spotify_object["type"] == "author":
            if "name" not in spotify_object:
                raise KeyError(f"No field `name` found in artist object: `{spotify_object}`")

            self.name = spotify_object["name"]

    def discord_display_str(self) -> str:
        if self.url:
            return f"[{self.name}]({self.url})"
        return self.name


class Collection:
    def __init__(self, spotify_object: dict) -> None:
        if spotify_object is None:
            raise ValueError("`Collection` class requires a spotify object")

        if "type" not in spotify_object:
            raise KeyError(f"Collection missing required field `type` in {spotify_object}`")
        self.type = spotify_object["type"]

        if "name" not in spotify_object:
            raise KeyError(f"No field `name` found in {self.type} object `{spotify_object}`")
        if "id" not in spotify_object:
            raise KeyError(f"No field `id` found in {self.type} object `{spotify_object}`")

        if self.type == "album":
            if "artists" not in spotify_object:
                raise KeyError(f"No field `artists` found in {self.type} object `{spotify_object}`")
            self.artists = []
            for artist in spotify_object["artists"]:
                self.artists.append(Artist(artist))
        
        elif self.type == "playlist":
            if "owner" not in spotify_object:
                raise KeyError(f"No field `owner` found in {self.type} object `{spotify_object}`")
            self.artists = [Artist(spotify_object["owner"]),]

        self.name = spotify_object["name"]
        self.id = spotify_object["id"]
        self.tracks = []
        self.get_tracks()

    def search_str(self) -> str:
        return f"{self.name} {self.artists[0].name}".lower()

    def get_tracks(self):
        response = requests.get(f"{SPOTIFY_API_PREFIX}/{self.type}s/{self.id}/tracks?limit=20", headers=get_spotify_headers())
        
        if response.status_code != 200:
            raise ControllerError(f"Failed to fetch tracks from Spotify for `Collection`. Status `{response.status_code}` and text `{response.text}`")

        body = json.loads(response.text)
        if "items" not in body:
            raise ControllerError(f"Received unexpected response from Spotify while fetching track info for `Collection` `{self.name}`")

        if self.type == "album": 
            for item in body["items"]:
                self.tracks.append(Queueable(item))

        elif self.type == "playlist":
            for item in body["items"]:
                self.tracks.append(Queueable(item["track"]))


class Queueable:
    def __init__(self, spotify_object: dict) -> None:
        print(spotify_object)
        if spotify_object is None:
            raise ValueError("`Queueable` class requires a spotify object")

        if "type" not in spotify_object:
            raise KeyError(f"No field `type` found in track/episode object `{spotify_object}`")
        self.type = spotify_object["type"]

        if self.type == "track":
            if "name" not in spotify_object:
                raise KeyError(f"No field `name` found in {self.type} object `{spotify_object}`")
            if "external_urls" not in spotify_object:
                raise KeyError(f"No field `external_urls` found in {self.type} object `{spotify_object}`")
            if "spotify" not in spotify_object["external_urls"]:
                raise KeyError(f"No field `spotify` found in {self.type} object['external_urls'] `{spotify_object}`")
            if "duration_ms" not in spotify_object:
                raise KeyError(f"No field `duration_ms` found in {self.type} object `{spotify_object}`")
            if "artists" not in spotify_object:
                raise KeyError(f"No field `artists` found in {self.type} object `{spotify_object}`")
            if "uri" not in spotify_object:
                raise KeyError(f"No field `uri` found in {self.type} object `{spotify_object}`")

            self.artists = []
            for artist in spotify_object["artists"]:
                self.artists.append(Artist(artist))

            try:
                self.image = spotify_object["album"]["images"][0]["url"]
            except: 
                self.image = None

            self.name = spotify_object["name"]
            self.url = spotify_object["external_urls"]["spotify"]
            self.duration_ms = spotify_object["duration_ms"]
            self.uri = spotify_object["uri"]

        elif self.type == "episode":
            if "name" not in spotify_object:
                raise KeyError(f"No field `name` found in {self.type} object `{spotify_object}`")
            if "external_urls" not in spotify_object:
                raise KeyError(f"No field `external_urls` found in {self.type} object `{spotify_object}`")
            if "spotify" not in spotify_object["external_urls"]:
                raise KeyError(f"No field `spotify` found in {self.type} object['external_urls'] `{spotify_object}`")
            if "duration_ms" not in spotify_object:
                raise KeyError(f"No field `duration_ms` found in {self.type} object `{spotify_object}`")
            if "images" not in spotify_object:
                raise KeyError(f"No field `images` found in {self.type} object `{spotify_object}`")
            if "show" not in spotify_object:
                raise KeyError(f"No field `show` found in {self.type} object `{spotify_object}`")
            if "uri" not in spotify_object:
                raise KeyError(f"No field `uri` found in {self.type} object `{spotify_object}`")

            self.artists = [Artist(spotify_object["show"]),]
            self.image = spotify_object["images"][0]["url"]
            self.name = spotify_object["name"]
            self.url = spotify_object["external_urls"]["spotify"]
            self.duration_ms = spotify_object["duration_ms"]
            self.uri = spotify_object["uri"]

        else:
            raise TypeError("`Queueable` class received unexpected type from Spotify. Must be one of episode,track")
            
    def search_str(self) -> str:
        return f"{self.name} {self.artists[0].name}".lower()

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
        if hours >= 1:
            human_duration += f"{hours}:"

        human_duration += f"{minutes}:"
        human_duration += f"{seconds}"
        return human_duration

    def discord_display_str(self):
        return f"**{self.name}** [{self.humanize_duration()}] by {self.artists[0].discord_display_str()}"


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


def get_now_playing() -> Queueable: 
    response = requests.get(f"{SPOTIFY_API_PREFIX}/me/player/queue", headers=get_spotify_headers())
    if response.status_code == 200:
        body = json.loads(response.text)
        try: 
            return Queueable(body["currently_playing"])
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
            queue.append(Queueable(track))
        except Exception as e:
            raise ControllerError(f"get_queue failed to create track info due to `{e}`")

    return queue


def clear_queue():
    queue = get_queue()
    headers = get_spotify_headers()
    for i in range(len(queue)):
        skip("next", headers=headers)

    try:
        skip("next", headers=headers)
    except:
        pass


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


def search(query: str, search_type: list[str], limit: int = 1):
    if len(search_type) == 0:
        raise ControllerError("spotify_controller.search expects at least one value in `search_type`")

    for t in search_type:
        if t not in ("album", "playlist", "track", "episode"):
            raise ValueError(f"`search_type` of spotify_controller.search must contain only 'album', 'playlist', 'track', 'episode'")

    type_str = ",".join(search_type)

    encoded_query = urllib.parse.quote_plus(query)
    response = requests.get(f"{SPOTIFY_API_PREFIX}/search?q={encoded_query}&type={type_str}&limit={limit}", headers=get_spotify_headers())

    if response.status_code != 200:
        raise ControllerError(f"spotify_controller.search failed with status `{response.status_code}` and text `{response.text}`")

    return json.loads(response.text)


def get_episode(id: str): 
    response = requests.get(f"{SPOTIFY_API_PREFIX}/episodes/{id}", headers=get_spotify_headers())
    if response.status_code == 200:
        return json.loads(response.text)
    elif response.status_code == 401:
        raise ControllerError("get_episode failed. Looks like you are logged out")
    else:
        raise ControllerError(f"get_episode failed with status `{response.status_code}` and text `{response.text}`")


def add_to_queue(uri: str): 
    encoded_uri = urllib.parse.quote(uri)
    response = requests.post(f"{SPOTIFY_API_PREFIX}/me/player/queue?uri={encoded_uri}&device_id={get_bot_device_id()}", headers=get_spotify_headers())
    if 300 > response.status_code >= 200:
        return response
   
    if response.status_code == 401: 
        raise ControllerError(f"add_to_queue failed. Looks like you are logged out")

    raise ControllerError(f"add_to_queue failed with response `{response.status_code}` and text `{response.text}`")


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
