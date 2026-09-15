from flask import Flask, request
import os
import base64
import requests
import json
import threading
import time

app = Flask(__name__)


def refresh_token_helper(refresh_token: str):
    """
    Performs the actual task of refreshing an expired access token as required in `clean_old_token` 
    and calls to the `refresh-token` endpoint. 

    :param refresh_token: The refresh_token to send to Spotify in order to get a new access token 
    """

    body = f"grant_type=refresh_token&client_id={os.getenv('SPOTIFY_CLIENT_ID')}&refresh_token={refresh_token}"
    encoded_auth = base64.b64encode(bytes(f"{os.getenv('SPOTIFY_CLIENT_ID')}:{os.getenv('SPOTIFY_CLIENT_SECRET')}", "utf-8"))
    headers = {
        "Authorization": f"Basic {encoded_auth.decode('utf-8')}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    response = requests.post(f"https://accounts.spotify.com/api/token", headers=headers, data=body)
    
    if 300 > response.status_code >= 200:
        body = json.loads(response.text)
        os.environ["SPOTIFY_ACCESS_TOKEN"] = body["access_token"]
        return {"access_token": body["access_token"]}, 200
    
    print(f"refresh_token failed with code {response.status_code} and text {response.text}")
    return {}


def clean_old_token(wait: int = 3590) -> bool:
    """
    Attempts to replace outdated access token after `wait` seconds. `wait` is usually defined by the 
    `expires_in` key in the authorization response from Spotify. By default, this is set 
    to just under 1 hour

    :param wait: The number of seconds to wait before replacing an outdated key
    :returns: `True` if the old token was successfully replaced. `False` otherwise
    """

    time.sleep(wait)
    if os.getenv("SPOTIFY_REFRESH_TOKEN") is None:
        return False

    response = refresh_token_helper(os.getenv("SPOTIFY_REFRESH_TOKEN"))
    if len(response) > 1 and 300 > response[1] >= 200:
        return True

    return False


@app.route("/callback", methods=["GET"])
def callback():
    """
    Handles communication from Spotify's auth server that a user has requested to login to 
    our client. Verifies that the user has a valid security token obtained from the client, 
    then forwards the request to Spotify to get an access token 

    # Required Query Args: 
    * `code` - A login code provided to the user by Spotify indicating that they logged 
               in successfully so far
    * `state` - A token obtained from the spotify client that indicates this is a valid 
                request, and not someone random hitting the server

    # Returns 
    If all goes well, will return a "Login Successful" plain text message 

    # Errors 
    * 500 - If the server does not have a security token set in the environment 
    * 401 - If the `state` arg does not match the expected value
    * 400 - If either `state` or `code` are missing, or if Spotify responds in an unexpected way
    """

    code = request.args.get("code")
    state = request.args.get("state")

    if os.getenv("AUTH_SERVER_SECURITY") is None:
        return {"error": "Problem fetching state"}, 500

    if state != os.getenv("AUTH_SERVER_SECURITY"):
        return {"error": "Received bad state"}, 401

    if state is None:
        return {"error": "Missing 'state' query parameter"}, 400
    if code is None:
        return {"error": "Missing 'code' query parameter"}, 400

    auth_form = f"code={code}&redirect_uri={os.getenv('AUTH_SERVER')}/callback&grant_type=authorization_code"
    encoded_auth = base64.b64encode(bytes(f"{os.getenv('SPOTIFY_CLIENT_ID')}:{os.getenv('SPOTIFY_CLIENT_SECRET')}", "utf-8"))
    headers = {
        "Authorization": f"Basic {encoded_auth.decode('utf-8')}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    response = requests.post("https://accounts.spotify.com/api/token", headers=headers, data=auth_form)
    if response.status_code == 200:
        body = json.loads(response.text)
        print(body)
        os.environ["SPOTIFY_ACCESS_TOKEN"] = body["access_token"]
        os.environ["SPOTIFY_REFRESH_TOKEN"] = body["refresh_token"]
        clean_thread = threading.Thread(target=clean_old_token, args=(body["expires_in"] - 10,))
        clean_thread.start()
        return "Login Successful", 200
    else:
        return response.text, 400


@app.route("/access-token/<state>", methods=["GET", "DELETE"])
def access_token(state: str):
    """
    First verifies that the request is coming from a valid client by checking the `state` argument. 
    Then responds with json containing {"access_token": "abcd", "refresh_token": "efgh"}

    # Required Positional Args
    * state - A token that indicates the request is coming from a valid client

    # Returns 
    If all goes well, responds with a json object containing the keys "access_token" and "refresh_token"

    # Errors 
    * 500 - If no security token has been set in the environment
    * 401 - If `state` does not match the security token in the environment
    * 404 - There is no spotify access token (likely indicating the user is logged out)
    """
    if os.getenv("AUTH_SERVER_SECURITY") is None:
        return {"error": "Problem fetching state"}, 500

    if state != os.getenv("AUTH_SERVER_SECURITY"):
        return {"error": "Received bad state"}, 401

    if request.method == "GET":
        return {
            "access_token": os.getenv("SPOTIFY_ACCESS_TOKEN"), 
            "refresh_token": os.getenv("SPOTIFY_REFRESH_TOKEN"),
        }, 200
    
    elif request.method == "DELETE": 
        status = 204
        if os.getenv("SPOTIFY_ACCESS_TOKEN") is not None:
            del os.environ["SPOTIFY_ACCESS_TOKEN"]
        else: 
            status = 404

        if os.getenv("SPOTIFY_REFRESH_TOKEN") is not None:
            del os.environ["SPOTIFY_REFRESH_TOKEN"]

        return {"status": status}, status


@app.route("/refresh-token", methods=["POST"])
def refresh_token(): 
    if not request.args.get("state"):
        return {"error": "Missing state argument"}, 400

    if not request.args.get("refresh_token"):
        return {"error": "Missing refresh_token argument"}, 400

    state = request.args.get("state")
    refresh_token = request.args.get("refresh_token")

    if os.getenv("AUTH_SERVER_SECURITY") is None:
        return {"error": "Problem fetching state"}, 500

    if state != os.getenv("AUTH_SERVER_SECURITY"):
        return {"error": "Received bad state"}, 401

    return refresh_token_helper(refresh_token)
        

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=False)
