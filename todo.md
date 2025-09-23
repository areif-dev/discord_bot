# Features 

- [x] cache access token, so you can skip logging in everytime the bot starts
  - [x] related: investigate refreshing the access token
- [x] get control functions (skip, pause, etc) working 
- [x] make bot leave if alone in the channel for some time
- [x] logout
- [ ] search through things other than tracks
  - [ ] have the option to display multiple results to user or just pick the first closest match
- [ ] killswitch
- [ ] playback gui

# Fixes 

- [x] .play command seems to append the entire existing queue followed by the requested song
- [x] potentially move references to the name 'Discord Bot' into an env var to allow customizing the bot name
- [x] break authentication server out into separate microservice
- [ ] make errors relating to being logged out more obvious
- [x] get docker builds on arm64 working
- [x] pause keeps streaming, then dumps all data rapidly when unpaused
  - [ ] still kind of happens if paused through spotify interface
- [x] maybe refetch auth token any time a command is called
  - Marked as complete. No longer necessary
