import os
import shutil
import subprocess
import sys
import time

from src.media.Media import VideoMedia


def ai_show_progress(process: subprocess.Popen,
                     temp_dir_in: str,
                     temp_dir_out: str,
                     is_srmd: bool):
    # FIXME: while checking files, sometimes the 'handler' changes files around
    #  which crashes the program.
    while True:  # While process is running
        if process.poll() is not None:
            print("")
            break

        # Show progress
        num_of_files_in: int = len(os.listdir(temp_dir_in))
        num_of_files_out: int = len(os.listdir(temp_dir_out))
        files_out_needed: int = num_of_files_in * 2
        if is_srmd:
            percentage_completed = \
                "{:.2f}".format(num_of_files_out / num_of_files_in * 100)
        else:
            percentage_completed = \
                "{:.2f}".format(num_of_files_out / files_out_needed * 100)
        sys.stdout.write(f"\rFiles in input: {num_of_files_in} | "
                         f"Files in output: {num_of_files_out} | "
                         f"{percentage_completed} % Completed |")
        sys.stdout.flush()
        time.sleep(2)


def __is_something_todo(current_video: VideoMedia,
                        resolution_threshold: str,
                        target_fps: float, ) -> bool:
    # Checking if there is something to do with that file
    if not current_video.is_under_resolution_threshold(resolution_threshold) and \
            current_video.get_estim_num_of_run(target_fps) == 0:
        print(f"Nothing to do with {current_video.filename}")
        return False
    return True


def __set_ffmpeg_output(is_out_file: bool, out_path, v_filename: str) -> str:
    # Output file for ffmpeg
    if is_out_file:
        return out_path[:-4]
    else:
        return f"{out_path}/{v_filename[:-4]}"


def __set_ffmpeg_params(vid_width: int, vid_height: int, target_fps: float):
    # Setting the parameters specific for the video
    # Estimating if RIFE needs UHD mode if it ever needs to run
    # And setting crf value
    # Limiting fps if resolution is too big
    if ((vid_width > 1920 and vid_height > 1080) or
            (vid_width > 1080 and vid_height > 1920)):
        print("Ultra HD mode is enabled.")
        uhd = "-u"
        crf_value = 28
        if (target_fps > 60 and
                ((vid_width >= 2560 and vid_height >= 1440) or
                 (vid_width >= 1440 and vid_height >= 2560))):
            print("The target FPS is set at 60 because the "
                  "video's resolution is higher than 2k.")
            target_fps = 60
        elif target_fps > 120:
            print("The target FPS is set at 120 because the "
                  "video's resolution is higher than 1080p.")
            target_fps = 120
    else:
        uhd = ""
        crf_value = 21
        print("Ultra HD mode is disabled.")
    return uhd, crf_value, target_fps


def __is_suffix_video(rec_suffixes: list[str], vid_suffix: str) -> bool:
    for suffix in rec_suffixes:
        if suffix == vid_suffix:
            return True
    return False


def __augment_resolution(current_video: VideoMedia,
                         resolution_threshold: str,
                         tmp_directory: str):
    if current_video.is_under_resolution_threshold(resolution_threshold):
        print("\nRunning SRMD to denoise the video.")
        os.chdir("../AIs/")
        process = subprocess.Popen(["./srmd-ncnn-vulkan",
                                    "-i", f"{tmp_directory}/in", "-o",
                                    f"{tmp_directory}/out", "-n", "8",
                                    "-s", "2"],
                                   shell=False,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        ai_show_progress(process, f"{tmp_directory}/in",
                         f"{tmp_directory}/out", True)
        shutil.rmtree(f"{tmp_directory}/in")
        os.rename(f"{tmp_directory}/out", f"{tmp_directory}/in")
        os.mkdir(f"{tmp_directory}/out")
        os.chdir("../..")
        print("\nFinished running SRMD.\n")


def __interpolate(current_video: VideoMedia, target_fps: float,
                  tmp_directory: str, uhd: str):
    number_of_iterations: int = current_video.get_estim_num_of_run(target_fps)
    if number_of_iterations > 0:
        print("\nRunning interpolation software.")
        os.chdir("../AIs/")
        print(f"It's going to run {number_of_iterations} times")

        for i in range(number_of_iterations):
            process = subprocess.Popen(["./rife-ncnn-vulkan", "-i",
                                        f"{tmp_directory}/in", "-o",
                                        f"{tmp_directory}/out", "-m",
                                        "rife-v2.3", f"{uhd}"], shell=False,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
            ai_show_progress(process, f"{tmp_directory}/in",
                             f"{tmp_directory}/out", False)
            current_video.fps = current_video.fps * 2
            shutil.rmtree(f"{tmp_directory}/in")
            os.rename(f"{tmp_directory}/out", f"{tmp_directory}/in")
            os.mkdir(f"{tmp_directory}/out")
        os.chdir("../..")
        print("\nFinished running interpolation software.")


def handler(options: dict, current_video: VideoMedia):
    recognized_suffixes_video: list[str] = \
        [".avi", ".mp4", ".mov", ".wmv", ".3gp", ".mpg", ".leotmv"]
    output_path: str = options["output"]
    tmp_directory: str = f"{options['temporaryDirectoryLocation']}/ave-tmp"
    is_output_file: bool = options["is_output_a_file"]
    target_fps: float = options["target_fps"]
    resolution_threshold: str = options['resolution_threshold']
    ffmpeg_output: str = ""
    crf_value: int = 0
    uhd: str = ""

    if not __is_something_todo(current_video,
                               resolution_threshold,
                               target_fps):
        print(f"Nothing needs to be done with {current_video.filename} . \n "
              f"Passing.")
        if not is_output_file:
            print("Copying anyway to output folder")
            shutil.copy(current_video.path, output_path)
        return

    # Output file for ffmpeg
    ffmpeg_output = __set_ffmpeg_output(is_output_file,
                                        output_path,
                                        current_video.filename)

    # setting ffmpeg parameters
    uhd, crf_value, target_fps = __set_ffmpeg_params(current_video.vid_width,
                                                     current_video.vid_height,
                                                     target_fps)

    # Starting the process
    if not __is_suffix_video(recognized_suffixes_video, current_video.suffix):
        print(f"The video suffix '{current_video.suffix}' "
              f"is not recognized... \nSkipping {current_video.filename} ...")
        return

    print("\nExtracting audio from video...")
    os.system(f"ffmpeg -loglevel error -stats -y -i {current_video.path} "
              f"-vn -c:a aac {tmp_directory}/audio.m4a")

    print("\nSegmenting video into temporary directory.")
    os.system(f"ffmpeg -loglevel error -stats -y -i {current_video.path} "
              f"-c:v copy -segment_time 00:02:00.00 "
              f"-f segment -reset_timestamps 1 "
              f"{tmp_directory}/vidin/%03d{current_video.suffix}")

    vids_input_folder: list[str] = os.listdir(f"{tmp_directory}/vidin")
    vids_input_folder.sort()

    filelist = open(f"{tmp_directory}/temporary_file.txt", "x")
    filelist.close()

    for selected_video in vids_input_folder:
        # Writing down the new location of video when it will finish to process
        filelist = open(f"{tmp_directory}/temporary_file.txt", "a")
        file_location = f"{tmp_directory}/vidout/{selected_video[:-4]}.mp4"
        filelist.write("file '%s'\n" % file_location)
        filelist.close()

        print("\nExtracting all frames from video into temporary directory.")
        os.system(f"ffmpeg -loglevel error -stats -y " 
                  f"-i {tmp_directory}/vidin/{vids_input_folder} "
                  f"-r {str(current_video.fps)} "
                  f"{current_video.get_color_profile_settings('png')} "
                  f"{tmp_directory}/in/%08d.png")

        __augment_resolution(current_video,
                             resolution_threshold,
                             tmp_directory)

        __interpolate(current_video, target_fps, tmp_directory, uhd)

        print(f"\nEncoding {vids_input_folder[:-4]}.mp4")
        os.system(f"ffmpeg -loglevel error -stats -y -framerate "
                  f"{current_video.get_exaggerated_fps(target_fps)} -i "
                  f"{tmp_directory}/in/%08d.png -c:v libx265 -crf {crf_value} "
                  f"-preset veryslow {current_video.ffmpeg_bitrate_command()} "
                  f"-r {target_fps} "
                  f"{current_video.get_color_profile_settings('vid')} "
                  f"{tmp_directory}/vidout/{vids_input_folder[:-4]}.mp4")

    # Writing the final result
    print(f"\nFinalizing {current_video.filename[:-4]}.mp4\n")
    os.system(f"ffmpeg -loglevel error -f concat -safe 0 -i "
              f"{tmp_directory}/temporary_file.txt -c copy "
              f"{ffmpeg_output}a.mp4")

    if os.path.exists(f"{tmp_directory}/audio.m4a"):  # If the video has audio
        os.system(f"ffmpeg -loglevel error -i {ffmpeg_output}a.mp4 "
                  f"-i {tmp_directory}/audio.m4a -c:a copy "
                  f"-c:v copy {ffmpeg_output}n.mp4")
    else:
        shutil.copy(f"{ffmpeg_output}a.mp4", f"{ffmpeg_output}n.mp4")

    os.system(f"ffmpeg -loglevel error -i {current_video.path} -i "
              f"{ffmpeg_output}n.mp4 -map 1 -c copy -map_metadata 0 "
              f"-tag:v hvc1 {ffmpeg_output}.mp4")

    os.remove(f"{ffmpeg_output}a.mp4")
    os.remove(f"{ffmpeg_output}n.mp4")