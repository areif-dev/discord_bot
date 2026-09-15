window.onSpotifyWebPlaybackSDKReady = () => {
  const token = '[My access token]';
  const player = new Spotify.Player({
    name: 'Web Playback SDK Quick Start Player',
    getOAuthToken: cb => { cb(token); },
    volume: 0.5
  });
}
