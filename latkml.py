import sys
sys.path.insert(0, './latk.py')
#sys.path.insert(1, './pix2pix-tensorflow')

import platform
osName = platform.system()

import os
from latk import *
from svgpathtools import *  # https://github.com/mathandy/svgpathtools
from PIL import Image # https://gist.github.com/n1ckfg/58b5425a1b81aa3c60c3d3af7703eb3b

def getCoordFromPathPoint(pt):
    point = str(pt)
    point = point.replace("(", "")
    point = point.replace("j)", "")
    point = point.split("+")

    x = 0
    y = 0

    try:
        point[0] = point[0].replace("j", "")
        x = float(point[0])
    except:
        pass
    try:
        point[1] = point[1].replace("j", "")
        y = float(point[1])
    except:
        pass

    return (x, y)

def getDistance2D(v1, v2):
    v1 = (v1[0], v1[1], 0)
    v2 = (v2[0], v2[1], 0)
    return sqrt((v1[0] - v2[0])**2 + (v1[1] - v2[1])**2 + (v1[2] - v2[2])**2)

def getDistance(v1, v2):
    return sqrt((v1[0] - v2[0])**2 + (v1[1] - v2[1])**2 + (v1[2] - v2[2])**2)

def getPathLength(path):
    firstPoint = getCoordFromPathPoint(path.point(0))
    lastPoint = getCoordFromPathPoint(path.point(1))
    return getDistance2D(firstPoint, lastPoint)

def getPixelLoc(pixels, x, y):
    col = list(pixels[int(x), int(y)])
    return (col[0]/255.0, col[1]/255.0, col[2]/255.0)

def loadImage(url):
    img = Image.open(url)
    img = img.convert('RGB')
    return img

def loadPixels(img):
    return img.load()

def saveImage(img, url): # https://stackoverflow.com/questions/14452824/how-can-i-save-an-image-with-pil
    img.save(url)

def newImage(width, height):
    return Image.new('RGB', (width, height))

def cropImage(img, x1, y1, x2, y2):
    box = (x1, y1, x2, y2)
    return img.crop(box)

def scaleImage(img, w, h):
    return img.resize((w, h), Image.ANTIALIAS)

def pasteImage(source, dest, x1, y1, x2, y2):
    box = (x1, y1, x2, y2)
    dest.paste(source, box)

def restoreXY(point):
    x = int(point.co[0] * 255.0)
    y = int(point.co[1] * -255.0)
    if (x < 0):
        x = 0
    elif (x > 255):
        x = 255
    if (y < 0):
        y = 0
    elif (y > 255):
        y = 255
    return (x, y)  


input_video="test.mp4"

at_path = "autotrace" # linux doesn't need path handled
ff_path = "ffmpeg"
if (osName == "Windows"):
    at_path = "\"C:\\Program Files\\AutoTrace\\autotrace\""
    ff_path = "\"C:\\Util\\ffmpeg\\bin\\ffmpeg\""
elif (osName == "Darwin"): # Mac
    at_path = "/Applications/autotrace.app/Contents/MacOS/autotrace"


# *** Step 1/5: Extract frames from source movie with ffmpeg. ***
os.makedirs("./pix2pix-tensorflow/files/input")
os.chdir("./pix2pix-tensorflow/files/input")
os.system(ff_path + " -i " + input_video + " -vf fps=12 image-%05d.png")


# *** Step 2/5: Resize to 512x256 with pil. ***
# TODO loop through all files
# https://code-maven.com/listing-a-directory-using-python
sourceImgUrl = "test.png"
sourceImg = loadImage(sourceImgUrl)
sourceDepthImg = cropImage(sourceImg, 80, 120, 560, 600)
sourceRgbImg = cropImage(sourceImg, 720, 120, 1200, 600)
sourceDepthImg = scaleImage(sourceDepthImg, 256, 256)
sourceRgbImg = scaleImage(sourceRgbImg, 256, 256)
destImg = newImage(512, 256)
pasteImage(sourceDepthImg, destImg, 0, 0, 256, 256)
pasteImage(sourceRgbImg, destImg, 256, 0, 512, 256)
saveImage(destImg, sourceImgUrl)


# *** Step 3/5: Process with Pix2pix. ***
os.chdir("../..")
os.system("python pix2pix.py --mode test --output_dir files/output --input_dir files/input --checkpoint files/model")


# *** Step 4/5: Convert Pix2pix png output to tga and run Autotrace. ***
at_bgcolor = "#000000"
at_color = 16
at_error_threshold=10
at_line_threshold=0
at_line_reversion_threshold=10

at_cmd = " -background-color=" + str(at_bgcolor) + " -color=" + str(at_color) + " -centerline -error-threshold=" + str(at_error_threshold) + "-line-threshold=" + str(at_line_threshold) + " -line-reversion-threshold=" + str(at_line_reversion_threshold)

os.chdir("files/output/images")

try:
    if (osName == "Windows"):
        os.system("dir")
        os.system("del *.tga")
        #os.system("for %i in (*-outputs.png) do magick %i -colorspace RGB -colorspace sRGB -depth 8 -alpha off %~nxi.tga")
        #os.system("for %i in (*.tga) do " + at_path + at_cmd + " -output=%~nxi.svg -output-format=svg %i")
        os.system("del *.tga")
    else:
        os.system("ls")
        os.system("rm *.tga")
        os.system("for file in *-outputs.png; do convert $file $file.tga; done")
        os.system("for file in *.tga; do " + at_path + " $file " + at_cmd + " -output-format=svg -output-file $file.svg; done")
        os.system("rm *.tga")
except:
    pass


# *** Step 5/5: Create final latk file from svg and image output. ***
la = Latk(init=True)

# TODO loop through all files
# https://code-maven.com/listing-a-directory-using-python

paths, attr = svg2paths("frame_00050-outputs.png.tga.svg")
pathLimit = 0.05
minPathPoints = 3
epsilon = 0.00005

for path in paths:
    numPoints = getPathLength(path)
    numRange = int(numPoints)
    if (numRange > 1):
        coords = []
        for i in range(numRange):
            pt = path.point(i/(numPoints-1))
            point = getCoordFromPathPoint(pt)
            coord = (point[0]/255.0, point[1]/-255.0, 0)
            if (i == 0):
                coords.append(coord)
            else:
                lastCoord = coords[len(coords)-1]
                if getDistance2D(coord, lastCoord) < pathLimit:
                    coords.append(coord)
                else:
                    coords = rdp(coords, epsilon=epsilon)
                    if (len(coords) >= minPathPoints):
                        la.setCoords(coords)
                    coords = []
                    coords.append(coord)
        coords = rdp(coords, epsilon=epsilon)            
        if (len(coords) >= minPathPoints):
            la.setCoords(coords)

img_depth = loadPixels(loadImage("frame_00050-inputs.png"))
img_rgb = loadPixels(loadImage("frame_00050-targets.png"))

for layer in la.layers:
    for frame in layer.frames:
        for stroke in frame.strokes:
            firstCoord = restoreXY(stroke.points[0])
            stroke.color = getPixelLoc(img_rgb, firstCoord[0], firstCoord[1])
            for point in stroke.points:
                coord = restoreXY(point)
                depth = getPixelLoc(img_depth, coord[0], coord[1])[0]
                point.co = (-point.co[0]/10.0, depth/10.0, point.co[1]/10.0)

la.write("test.latk")