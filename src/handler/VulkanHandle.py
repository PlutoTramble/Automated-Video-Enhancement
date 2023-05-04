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




def handler(options: dict, current_video: VideoMedia):
    suffixes_video: list[str] = \
        [".avi", ".mp4", ".mov", ".wmv", ".3gp", ".mpg", ".leotmv"]
    output_path: str = options["output"]
    tmp_directory: str = f"{options['temporaryDirectoryLocation']}/ave-tmp"
    is_output_file: bool = options["is_output_a_file"]
    target_fps: float = options["target_fps"]
    resolution_threshold: str = options['resolution_threshold']
    ffmpeg_output: str = ""
    crf_value: int = 0
    uhd = ""

    if not __is_something_todo(current_video,
                               resolution_threshold,
                               target_fps):
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

    # TODO : do rewrite of function from here
    # Starting the process
    for suffix in suffixes_video:  # Checking the video suffix
        if current_video.suffix == suffix:
            print("\nExtracting audio from video...")
            os.system(f"ffmpeg -loglevel error -stats -y -i {current_video.path} " \
                      f"-vn -c:a aac {tmp_directory}/audio.m4a")

            print("\nSegmenting video into temporary directory.")
            os.system(f"ffmpeg -loglevel error -stats -y -i {current_video.path} " \
                      f"-c:v copy -segment_time 00:02:00.00 " \
                      f"-f segment -reset_timestamps 1 {tmp_directory}/vidin/%03d{current_video.suffix}")

            videosInFolder = os.listdir(f"{tmp_directory}/vidin")
            videosInFolder.sort()

            filelist = open(f"{tmp_directory}/temporary_file.txt", "x")
            filelist.close()

            for vidInFolder in videosInFolder:
                # Writing down the new location of video when it will finish to process
                filelist = open(f"{tmp_directory}/temporary_file.txt", "a")
                fileLocation = f"{tmp_directory}/vidout/{vidInFolder[:-4]}.mp4"
                filelist.write("file '%s'\n" % fileLocation)
                filelist.close()

                print("\nExtracting all frames from video into temporary directory.")
                os.system(f"ffmpeg -loglevel error -stats -y " \
                          f"-i {tmp_directory}/vidin/{vidInFolder} " \
                          f"-r {str(current_video.fps)} {current_video.getColorProfileSettings('png')} " \
                          f"{tmp_directory}/in/%08d.png")

                # SRMD
                if current_video.isUnderResolutionThreshold(resolution_threshold):
                    print("\nRunning SRMD to denoise the video.")
                    os.chdir("../AIs/")
                    process = subprocess.Popen(["./srmd-ncnn-vulkan", \
                                                "-i", f"{tmp_directory}/in", "-o", \
                                                f"{tmp_directory}/out", "-n", "8", "-s", "2"], \
                                               shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    AIRunning(process, f"{tmp_directory}/in", f"{tmp_directory}/out", True)
                    shutil.rmtree(f"{tmp_directory}/in")
                    os.rename(f"{tmp_directory}/out", f"{tmp_directory}/in")
                    os.mkdir(f"{tmp_directory}/out")
                    os.chdir("../..")
                    print("\nFinished running SRMD.\n")

                # Interpolation
                if current_video.getEstimNumOfRun != 0:
                    print("\nRunning interpolation software.")
                    os.chdir("../AIs/")
                    print(f"It's going to run {current_video.getEstimNumOfRun(target_fps)} times")

                    for i in range(current_video.getEstimNumOfRun(target_fps)):
                        # process = ""
                        # if ((pVideo.vidWidth > 1920 and pVideo.vidHeight > 1080) or \
                        #         (pVideo.vidWidth > 1080 and pVideo.vidHeight > 1920)) or \
                        #         (pVideo.fps <= 25) or \
                        #         (len(os.listdir(f"{tmp_directory}/in")) >= 3235): # tmp: ifrnet can't do more than 3235 images in 1080p
                        #     process = subprocess.Popen(["./rife-ncnn-vulkan", "-i", \
                        #         f"{tmp_directory}/in", "-o", f"{tmp_directory}/out", "-m", \
                        #         "rife-v2.3", f"{uhd}"], shell=False, \
                        #         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        #     print("Running RIFE...")
                        # else:
                        #     process = subprocess.Popen(["./ifrnet-ncnn-vulkan", "-i", \
                        #         f"{tmp_directory}/in", "-o", f"{tmp_directory}/out", "-m", \
                        #         "IFRNet_L_Vimeo90K", f"{uhd}"], \
                        #         shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        #     print("Running IFRNet")
                        process = subprocess.Popen(["./rife-ncnn-vulkan", "-i", \
                                                    f"{tmp_directory}/in", "-o", f"{tmp_directory}/out", "-m", \
                                                    "rife-v2.3", f"{uhd}"], shell=False, \
                                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        AIRunning(process, f"{tmp_directory}/in", f"{tmp_directory}/out", False)
                        current_video.fps = current_video.fps * 2
                        shutil.rmtree(f"{tmp_directory}/in")
                        os.rename(f"{tmp_directory}/out", f"{tmp_directory}/in")
                        os.mkdir(f"{tmp_directory}/out")

                    os.chdir("../..")
                    print("\nFinished running interpolation software.")

                print(f"\nEncoding {vidInFolder[:-4]}.mp4")
                os.system(f"ffmpeg -loglevel error -stats " \
                          f"-y -framerate {current_video.getExageratedFPS(target_fps)} " \
                          f"-i {tmp_directory}/in/%08d.png -c:v libx265 -crf {crf_value} " \
                          f"-preset veryslow {current_video.ffmpegBitrateCommand()} -r {target_fps} " \
                          f"{current_video.getColorProfileSettings('vid')} " \
                          f"{tmp_directory}/vidout/{vidInFolder[:-4]}.mp4")

            ## Writing the final result
            print(f"\nFinalizing {current_video.filename[:-4]}.mp4\n")
            os.system(f"ffmpeg -loglevel error -f concat -safe 0 " \
                      f"-i {tmp_directory}/temporary_file.txt -c copy {ffmpeg_output}a.mp4")

            if os.path.exists(f"{tmp_directory}/audio.m4a"):  # If the video has audio
                os.system(f"ffmpeg -loglevel error -i {ffmpeg_output}a.mp4 " \
                          f"-i {tmp_directory}/audio.m4a -c:a copy " \
                          f"-c:v copy {ffmpeg_output}n.mp4")
            else:
                shutil.copy(f"{ffmpeg_output}a.mp4", f"{ffmpeg_output}n.mp4")

            os.system(f"ffmpeg -loglevel error -i {current_video.path} -i {ffmpeg_output}n.mp4 " \
                      f"-map 1 -c copy -map_metadata 0 -tag:v hvc1 {ffmpeg_output}.mp4")

            os.remove(f"{ffmpeg_output}a.mp4")
            os.remove(f"{ffmpeg_output}n.mp4")
