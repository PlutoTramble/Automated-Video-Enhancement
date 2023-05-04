import os
import sys

import cv2
from pathlib import Path


class Video:
    def __init__(self, path: str):
        try:
            self.__video = cv2.VideoCapture(path)
        except IOError(f"cv2 couldn't process that file : {path}"):
            sys.exit(2)

        # Frames
        self.fps = float(self.__video.get(cv2.CAP_PROP_FPS))
        self.vidTotalFrames = (self.__video.get(cv2.CAP_PROP_FRAME_COUNT))

        # Resolution
        self.vidWidth = int(self.__video.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.vidHeight = int(self.__video.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Path and filename
        self.path = path
        self.filename = os.path.basename(self.path)
        self.suffix = Path(self.filename.lower()).suffix

    # How many times does the interpolation AI
    # needs to run to reach the target frame per second
    def get_estim_num_of_run(self, target_FPS):
        ## FIXME What if target_FPS is null
        number_of_times = 0
        future_FPS = self.fps
        while future_FPS < target_FPS:
            future_FPS *= 2
            number_of_times += 1
        return number_of_times

    # It is necessary for encoding from png files to video
    def get_exagerated_FPS(self, target_FPS):
        ## FIXME What if target_FPS is null
        future_FPS = self.fps
        while future_FPS < target_FPS:
            future_FPS *= 2
        return future_FPS

    ## FIXME handle properly color profile
    # Sets the color profile settings for ffmpeg
    def get_color_profile_settings(self, vid_or_png: str):
        if vid_or_png.lower() != 'vid' or vid_or_png.lower() != 'png':
            raise IOError("The option is either 'vid' or 'png'.")

        color_info = os.popen(f"ffprobe -v error -show_entries "
                              f"stream=pix_fmt,color_space,color_range,"
                              f"color_transfer,color_primaries -of "
                              f"default=noprint_wrappers=1 {self.path}") \
            .read().splitlines()

        color_setting_vid = ""

        pixel_format = color_info[0][8:]
        if not pixel_format == 'unknown':
            color_setting_vid += "-pix_fmt " + pixel_format
        else:
            color_setting_vid += "-pix_fmt yuv420p"

        color_setting_png = "-pix_fmt rgb24"

        color_space = color_info[2][12:]
        if color_space is not 'unknown':
            color_setting_vid += " -colorspace " + color_space
            color_setting_png += " -colorspace " + color_space

        colorPrimaries = color_info[4][16:]
        if colorPrimaries is not 'unknown':
            color_setting_vid += " -color_primaries " + colorPrimaries
            color_setting_png += " -color_primaries " + colorPrimaries

        if vid_or_png.lower() is 'vid':
            return color_setting_vid
        else:
            return color_setting_png

    # True if the current video is under the resolution threshold
    def is_under_resolution_threshold(self, width_x_height: str):
        width_threshold = int(width_x_height.lower().split('x')[0])
        height_threshold = int(width_x_height.lower().split('x')[1])
        if ((width_threshold >= self.vidWidth and
             height_threshold >= self.vidHeight) or
                (height_threshold >= self.vidWidth and
                 width_threshold >= self.vidHeight)):
            return True
        else:
            return False

    # To fix too much bitrate for certain videos
    def ffmpeg_bitrate_command(self):
        total_seconds_duration = float(self.vidTotalFrames / self.fps)
        filesize = os.path.getsize(self.path)
        bitrate = int((filesize / total_seconds_duration) / 1024 * 8)

        # The option will not work if it's under 1080p
        if (self.vidWidth <= 1920 and self.vidHeight <= 1080) or \
                (self.vidWidth <= 1080 and self.vidHeight <= 1920):
            return ""

        if bitrate < 10000:
            return ""
        elif bitrate > 40000:
            return "-maxrate 40000k -bufsize 40000k"
        elif bitrate > 20000:
            bitrate = bitrate + ((bitrate * 20) / 100)
            return f"-maxrate {bitrate} -bufsize {bitrate}"
        elif bitrate >= 10000:
            bitrate = bitrate + ((bitrate * 20) / 100)
            return f"-maxrate {bitrate} -bufsize {bitrate}"
