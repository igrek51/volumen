#!/usr/bin/env python3
import os
import re
import time

import gi

gi.require_version('Notify', '0.7')
from gi.repository import Notify
import os.path

from nuclear import CliBuilder, subcommand
from nuclear.sublog import log, log_error
from nuclear.utils.shell import shell, shell_output

volume_step = 1


def main():
    with log_error():
        CliBuilder('volumen', help='Volume notification tool').has(
            subcommand('up', run=volume_up, help='Increase volume level'),
            subcommand('down', run=volume_down, help='Decrease volume level'),
            subcommand('show', run=volume_show, help='Show current volume level'),
            subcommand('spotify', run=volume_show, help='Show current volume level').has(
                subcommand('pause', run=spotify_pause, help='Pause spotify'),
                subcommand('previous', run=spotify_pause, help='Previous spotify song'),
                subcommand('next', run=spotify_pause, help='Next spotify song'),
            ),
        ).run()


def volume_up():
    shell(f'amixer -q sset Master {volume_step}%+')
    volume_show()


def volume_down():
    shell(f'amixer -q sset Master {volume_step}%-')
    volume_show()


def volume_show():
    master_volume = read_master_volume()
    icon_name = get_notification_icon(master_volume)
    summary = 'Volume'
    body = f'{master_volume:d}%'
    show_notification(icon_name, summary, body)


def read_master_volume():
    return read_pulseaudio_volume()


def get_pulseaudio_sink_number():
    master_volume_regex = r'^(\d+)(.*)$'
    for line in shell_output('pactl list sinks short').split('\n'):
        match = re.match(master_volume_regex, line)
        if match:
            return int(match.group(1))
    return None


def read_pulseaudio_volume():
    master_volume_regex = r'^(.*)Volume: front-left: \d+ / +(\d+)% / (.*)$'
    for line in shell_output('pactl list sinks').split('\n'):
        match = re.match(master_volume_regex, line)
        if match:
            return int(match.group(2))
    log.warn('Master volume could not have been read')
    return None


def read_alsa_volume():
    master_volume_regex = r'^.*Mono: Playback \d+ \[(\d+)%\] \[(-?\d+\.?\d*)dB\] \[on\]$'
    for line in shell_output('amixer get Master').split('\n'):
        match = re.match(master_volume_regex, line)
        if match:
            return int(match.group(1))
    log.warn('Master volume could not have been read')
    return None


def get_notification_icon(volume):
    if volume is None:
        return 'audio-card'
    if volume == 0:
        return "notification-audio-volume-off"
    elif volume < 30:
        return "notification-audio-volume-low"
    elif volume < 60:
        return "notification-audio-volume-medium"
    else:
        return "notification-audio-volume-high"


def save_current_body(current_file, body):
    f = open(current_file, 'w')
    f.write(body)
    f.close()


def current_millis():
    return int(round(time.time() * 1000))


def show_notification(icon_name, summary, body):
    current_volume_file = '/tmp/volumen-current'

    if os.path.isfile(current_volume_file):
        save_current_body(current_volume_file, body)
        # skip - another process is displaying notification
        return
    save_current_body(current_volume_file, body)

    Notify.init("volumen")
    notification = Notify.Notification.new(
        summary,
        body,
        icon_name
    )
    notification.show()

    # monitor for changes
    start = current_millis()
    while current_millis() < start + 1000:
        if os.path.isfile(current_volume_file):
            f = open(current_volume_file, 'r')
            newBody = f.read()
            if body != newBody:  # body changed
                body = newBody
                notification.update(summary, body, icon_name)
                notification.show()
                # reset timer
                start = current_millis()
        time.sleep(0.05)

    notification.close()

    os.remove(current_volume_file)


def spotify_pause():
    shell(
        'dbus-send --print-reply --dest=org.mpris.MediaPlayer2.spotify /org/mpris/MediaPlayer2 '
        'org.mpris.MediaPlayer2.Player.PlayPause')


def spotify_next():
    shell(
        'dbus-send --print-reply --dest=org.mpris.MediaPlayer2.spotify /org/mpris/MediaPlayer2 '
        'org.mpris.MediaPlayer2.Player.Next')


def spotify_previous():
    shell(
        'dbus-send --print-reply --dest=org.mpris.MediaPlayer2.spotify /org/mpris/MediaPlayer2 '
        'org.mpris.MediaPlayer2.Player.Previous')


if __name__ == '__main__':
    main()
