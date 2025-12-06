#!/usr/bin/env bash

update_ubuntu () {
    sudo apt update -y 
    sudo apt upgrade -y 
}

update_fedora () {
    sudo dnf update -y
}

if awk -F= '/^NAME/{print $2}' /etc/os-release | grep Ubuntu; then
    update_ubuntu
elif awk -F= '/^NAME/{print $2}' /etc/os-release | grep Fedora; then
    update_fedora
else 
    echo "Unsupported OS detected"
fi

rustup update 
cargo install librespot
