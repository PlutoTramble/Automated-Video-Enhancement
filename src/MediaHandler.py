## FIXME Instead of os.system, do subprocess.
import sys
import cv2
import os
from pathlib import Path
import shutil
import subprocess
import time

class video:
    def __init__(self, pPath: str):
        try:
            self.__video = cv2.VideoCapture(pPath)
        except IOError(f"cv2 couldn't process that file : {pPath}"):
            sys.exit(2)

        # Frames
        self.fps = float(self.__video.get(cv2.CAP_PROP_FPS))
        self.vidTotalFrames = (self.__video.get(cv2.CAP_PROP_FRAME_COUNT))

        # Resolution
        self.vidWidth = int(self.__video.get(cv2.CAP_PROP_FRAME_WIDTH ))
        self.vidHeight = int(self.__video.get(cv2.CAP_PROP_FRAME_HEIGHT ))

        # Path and filename
        self.path = pPath
        self.filename = os.path.basename(self.path)
        self.suffix = Path(self.filename.lower()).suffix

    # How many times does the interpolation AI
    # needs to run to reach the target frame per second
    def getEstimNumOfRun(self, pTargetFPS):
        numberOfTimes = 0
        futureFPS = self.fps
        while futureFPS < pTargetFPS:
            futureFPS *= 2
            numberOfTimes += 1

        return numberOfTimes

    # It is necessary for encoding
    def getExageratedFPS(self, pTargetFPS):
        futureFPS = self.fps
        while futureFPS < pTargetFPS:
            futureFPS *= 2
        
        return futureFPS

    #Sets the color profile settings for ffmpeg
    def getColorProfileSettings(self, pVidOrPng:str): ## FIXME handle properly color profile
        colorInfo = os.popen(f"ffprobe -v error -show_entries "\
            f"stream=pix_fmt,color_space,color_range,"\
            f"color_transfer,color_primaries -of "\
            f"default=noprint_wrappers=1 {self.path}").read().splitlines()
	
        pixelFormat = colorInfo[0][8:]
        if not pixelFormat == 'unknown':
            colorSettingsVid = "-pix_fmt " + pixelFormat
        else:
            colorSettingsVid = "-pix_fmt yuv420p"
        colorSettingsPng = "-pix_fmt rgb24"

        colorSpace = colorInfo[2][12:]
        if not colorSpace == 'unknown':
            colorSettingsVid += " -colorspace " + colorSpace
            colorSettingsPng += " -colorspace " + colorSpace

        colorPrimaries = colorInfo[4][16:]
        if not colorPrimaries == 'unknown':
            colorSettingsVid += " -color_primaries " + colorPrimaries
            colorSettingsPng += " -color_primaries " + colorPrimaries

        if pVidOrPng.lower() == 'vid':
            return colorSettingsVid
        elif pVidOrPng.lower() == 'png':
            return colorSettingsPng
        else:
            raise IOError("The option is either 'vid' or 'png'.")

    # True if the current video is under the resolution threshold
    def isUnderResolutionThreshold(self, pWidthxHeight:str):
        widthThreshold = int(pWidthxHeight.lower().split('x')[0])
        heightThreshold = int(pWidthxHeight.lower().split('x')[1])
        if ((widthThreshold >= self.vidWidth and heightThreshold >= self.vidHeight) or \
                (heightThreshold >= self.vidWidth and widthThreshold >= self.vidHeight)):
            return True
        else:
            return False

    # To fix too much bitrate for certain videos
    def ffmpegBitrateCommand(self):
        totalSecondsDuration = float(self.vidTotalFrames / self.fps)
        filesize = os.path.getsize(self.path)
        bitrate = int((filesize/totalSecondsDuration)/1024*8)

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
        elif bitrate > 10000:
            bitrate = bitrate + ((bitrate * 20) / 100)
            return f"-maxrate {bitrate} -bufsize {bitrate}"




def AIRunning(pProcess: subprocess.Popen, pTempDirIn:str, pTempDirOut:str, isSRMD: bool):
    while True: # While process is running
        if pProcess.poll() is not None:
            print("")
            break
        else:
            #Show progress
            numOfFilesIn = len(os.listdir(pTempDirIn))
            numOfFilesOut = len(os.listdir(pTempDirOut))
            filesOutNeeded = numOfFilesIn * 2
            if isSRMD:
                percentageCompleted = "{:.2f}".format(numOfFilesOut/numOfFilesIn*100)
            else:
                percentageCompleted = "{:.2f}".format(numOfFilesOut/filesOutNeeded*100)
            sys.stdout.write(f"\rFiles in input: {numOfFilesIn} | "\
                f"Files in output: {numOfFilesOut} | "\
                f"{percentageCompleted} % Completed |")
            sys.stdout.flush()
            time.sleep(5)

def Handler(pOptions:dict, pVideo:video):
    suffixesVideo = [".avi", ".mp4", ".mov", ".wmv", ".3gp", ".mpg", ".leotmv"]
    outputPath = pOptions["output"]
    tmpDirectory = f"{pOptions['temporaryDirectoryLocation']}/ave-tmp"
    outputIsFile = pOptions["isOutputAFile"]
    targetFPS = pOptions["targetFPS"]
    resolutionThreshold = pOptions['resolutionThreshold']
    ffmpegOutput = ""
    crfValue = 0
    uhd = ""

    # Checking if there is something to do with that file
    if not pVideo.isUnderResolutionThreshold(resolutionThreshold) and \
            pVideo.getEstimNumOfRun(targetFPS) == 0:
        print(f"Nothing to do with {pVideo.filename}")

        if not outputIsFile:
            print("Copying anyway to output folder")
            shutil.copy(pVideo.path, outputPath)
        
        return

    # Output file for ffmpeg
    if outputIsFile:
        ffmpegOutput = outputPath[:-4]
    else:
        ffmpegOutput = f"{outputPath}/{pVideo.filename[:-4]}"

    ## Setting the parameters specific for the video
    # Estimating if RIFE needs UHD mode if it ever needs to run
    # And setting crf value
    # Limiting fps if resolution is too big
    if (pVideo.vidWidth > 1920 and pVideo.vidHeight > 1080) or \
            (pVideo.vidWidth > 1080 and pVideo.vidHeight > 1920):
        print("Ultra HD mode is enabled.")
        uhd = "-u"
        crfValue = 26
        if targetFPS > 60 and \
            ((pVideo.vidWidth > 2560 and pVideo.vidHeight > 1440) or \
            (pVideo.vidWidth > 1440 and pVideo.vidHeight > 2560)):
            print("The target FPS is set at 60 because the "\
                "video's resolution is higher than 2k.")
            targetFPS = 60
        elif targetFPS > 120:
            print("The target FPS is set at 120 because the "\
                "video's resolution is higher than 1080p.")
            targetFPS = 120
    else:
        crfValue = 19
        print("Ultra HD mode is disabled.")
            
    ## Starting the process
    for suffix in suffixesVideo: #Checking the video suffix
        if pVideo.suffix == suffix:
            print("\nExtracting audio from video...")
            os.system(f"ffmpeg -loglevel error -stats -y -i {pVideo.path} "\
                f"-vn -c:a aac {tmpDirectory}/audio.m4a")

            print("\nSegmenting video into temporary directory.")
            os.system(f"ffmpeg -loglevel error -stats -y -i {pVideo.path} "\
                f"-c:v copy -segment_time 00:02:00.00 "\
                f"-f segment -reset_timestamps 1 {tmpDirectory}/vidin/%03d{pVideo.suffix}")
            
            videosInFolder = os.listdir(f"{tmpDirectory}/vidin")
            videosInFolder.sort()

            filelist = open(f"{tmpDirectory}/temporary_file.txt", "x")
            filelist.close()

            for vidInFolder in videosInFolder:
                # Writing down the new location of video when it will finish to process
                filelist = open(f"{tmpDirectory}/temporary_file.txt", "a")
                fileLocation = f"{tmpDirectory}/vidout/{vidInFolder[:-4]}.mp4"
                filelist.write("file '%s'\n" %fileLocation)
                filelist.close()

                print("\nExtracting all frames from video into temporary directory.")
                os.system(f"ffmpeg -loglevel error -stats -y "\
                    f"-i {tmpDirectory}/vidin/{vidInFolder} "\
                    f"-r {str(pVideo.fps)} {pVideo.getColorProfileSettings('png')} "\
                    f"{tmpDirectory}/in/%08d.png")

                # SRMD
                if pVideo.isUnderResolutionThreshold(resolutionThreshold):
                    print("\nRunning SRMD to denoise the video.")
                    os.chdir("../AIs/")
                    process = subprocess.Popen(["./srmd-ncnn-vulkan", \
                        "-i", f"{tmpDirectory}/in", "-o", \
                        f"{tmpDirectory}/out", "-n", "8", "-s", "2"], \
                        shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    AIRunning(process, f"{tmpDirectory}/in", f"{tmpDirectory}/out", True)
                    shutil.rmtree(f"{tmpDirectory}/in")
                    os.rename(f"{tmpDirectory}/out", f"{tmpDirectory}/in")
                    os.mkdir(f"{tmpDirectory}/out")
                    os.chdir("../..")
                    print("\nFinished running SRMD.\n")

                #Interpolation
                if pVideo.getEstimNumOfRun != 0:
                    print("\nRunning interpolation software.")
                    os.chdir("../AIs/")
                    print(f"It's going to run {pVideo.getEstimNumOfRun(targetFPS)} times")

                    for i in range(pVideo.getEstimNumOfRun(targetFPS)):
                        #process = ""
                        # if ((pVideo.vidWidth > 1920 and pVideo.vidHeight > 1080) or \
                        #         (pVideo.vidWidth > 1080 and pVideo.vidHeight > 1920)) or \
                        #         (pVideo.fps <= 25) or \
                        #         (len(os.listdir(f"{tmpDirectory}/in")) >= 3235): # tmp: ifrnet can't do more than 3235 images in 1080p
                        #     process = subprocess.Popen(["./rife-ncnn-vulkan", "-i", \
                        #         f"{tmpDirectory}/in", "-o", f"{tmpDirectory}/out", "-m", \
                        #         "rife-v2.3", f"{uhd}"], shell=False, \
                        #         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        #     print("Running RIFE...")
                        # else:
                        #     process = subprocess.Popen(["./ifrnet-ncnn-vulkan", "-i", \
                        #         f"{tmpDirectory}/in", "-o", f"{tmpDirectory}/out", "-m", \
                        #         "IFRNet_L_Vimeo90K", f"{uhd}"], \
                        #         shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        #     print("Running IFRNet")
                        process = subprocess.Popen(["./rife-ncnn-vulkan", "-i", \
                            f"{tmpDirectory}/in", "-o", f"{tmpDirectory}/out", "-m", \
                            "rife-v2.3", f"{uhd}"], shell=False, \
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        AIRunning(process, f"{tmpDirectory}/in", f"{tmpDirectory}/out", False)
                        pVideo.fps = pVideo.fps * 2
                        shutil.rmtree(f"{tmpDirectory}/in")
                        os.rename(f"{tmpDirectory}/out", f"{tmpDirectory}/in")
                        os.mkdir(f"{tmpDirectory}/out")

                    os.chdir("../..")
                    print("\nFinished running interpolation software.")

                print(f"\nEncoding {vidInFolder[:-4]}.mp4")
                os.system(f"ffmpeg -loglevel error -stats "\
                    f"-y -framerate {pVideo.getExageratedFPS(targetFPS)} "\
                    f"-i {tmpDirectory}/in/%08d.png -c:v libx265 -crf {crfValue} "\
                    f"-preset veryslow {pVideo.ffmpegBitrateCommand()} -r {targetFPS} "\
                    f"{pVideo.getColorProfileSettings('vid')} "\
                    f"{tmpDirectory}/vidout/{vidInFolder[:-4]}.mp4")

            ## Writing the final result
            print(f"\nFinalizing {pVideo.filename[:-4]}.mp4\n")
            os.system(f"ffmpeg -loglevel error -f concat -safe 0 "\
                f"-i {tmpDirectory}/temporary_file.txt -c copy {ffmpegOutput}a.mp4")

            if os.path.exists(f"{tmpDirectory}/audio.m4a"): # If the video has audio
                os.system(f"ffmpeg -loglevel error -i {ffmpegOutput}a.mp4 "\
                f"-i {tmpDirectory}/audio.m4a -c:a copy "\
                f"-c:v copy {ffmpegOutput}n.mp4")
            else:
                shutil.copy(f"{ffmpegOutput}a.mp4", f"{ffmpegOutput}n.mp4")
            
            os.system(f"ffmpeg -loglevel error -i {pVideo.path} -i {ffmpegOutput}n.mp4 "\
            f"-map 1 -c copy -map_metadata 0 -tag:v hvc1 {ffmpegOutput}.mp4")

            os.remove(f"{ffmpegOutput}a.mp4")
            os.remove(f"{ffmpegOutput}n.mp4")