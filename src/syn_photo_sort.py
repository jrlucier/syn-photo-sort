#!/usr/bin/python

import sys
import fnmatch
import os
import platform
import shutil
import hashlib
import traceback
import subprocess
import os.path
import datetime
import argparse
import time
from datetime import datetime

######################## Functions #########################

#TODO: junk mobile photos: FB_*,  *-ANIMATION.gif, *-COLLAGE*

def removeEmptyFolders(path, removeRoot=True):
  'Function to remove empty folders'
  if not os.path.isdir(path):
    return

  # remove empty subfolders
  files = os.listdir(path)
  if len(files):
    for f in files:
      fullpath = os.path.join(path, f)
      if os.path.isdir(fullpath):
        removeEmptyFolders(fullpath)

  # if folder empty, delete it
  files = os.listdir(path)
  if len(files) == 0 and removeRoot:
    os.rmdir(path)

def checkForExiv2():
  "Ensures we have exiv2 installed" 
  try:
    devnull = open(os.devnull)
    subprocess.Popen(['exiv2'], stdout=devnull, stderr=devnull).communicate()
  except OSError as e:
    if e.errno == os.errno.ENOENT:
      print 'Exiv2 not installed!'
      sys.exit(1)

def outputFromExiv2(f):
  "Output from exiv2.  We consume the errors and output from std out"
  try:
    return subprocess.check_output(['exiv2', f, '-g', 'Exif.Photo.DateTimeOriginal', '-Pv'], stderr=subprocess.STDOUT)
  except subprocess.CalledProcessError:
    return '' 

def photoDate(f):
  "Return the date/time on which the given photo was taken. Uses exiv2, on Synology by default"
  output = outputFromExiv2(f)
  if(not output or 'unknown image type' in output):
    # No Exif, use modified date/time
    return creationDate(f)
    
  try:   
    return datetime.strptime(output.split('\n')[0].lstrip(), "%Y:%m:%d %H:%M:%S")
  except ValueError:
    # Couldn't parse the field, probably bad exif data
    return creationDate(f)

def creationDate(f):
  "Gets a DateTime from a files creation date via the file system"
  if platform.system() == 'Windows':
    return datetime.fromtimestamp(os.path.getctime(f))
  else:
    stat = os.stat(f)
    try:
      return datetime.fromtimestamp(stat.st_birthtime)
    except AttributeError:
      # We're probably on Linux. No easy way to get creation dates here,
      # so we'll settle for when its content was last modified.
      return datetime.fromtimestamp(stat.st_mtime)

def filenameExtension(f):
  "Return the file extension normalized to lowercase."
  return os.path.splitext(f)[1][1:].strip().lower()

def handleFileMove(f, filename, fFmtName, problems, move, sourceDir, destDir, errorDir):
  fExt = filenameExtension(f)

  # Copy photos/videos into year and month subfolders. Name the copies according to
  # their timestamps. If more than one photo/video has the same timestamp, add
  # suffixes 0001, 0002, 0003, etc. to the names. 

  suffix = 1
  try:
    pDate = photoDate(f)
    yr = pDate.year
    mo = pDate.month
    moTxt = pDate.strftime("%b").upper()
    day = pDate.day
    fHash = None
    
    destFileName = pDate.strftime(fFmtName)
    thisDestDir = destDir + '/%04d/%02d/%02d%s%04d' % (yr, mo, day, moTxt, yr)
    
    if not os.path.exists(thisDestDir):
      os.makedirs(thisDestDir)

    duplicate = thisDestDir + '/%s.' % (destFileName) + fExt
    skipCopy = False
    while os.path.exists(duplicate):

      # We found a duplicate at the destination, get the incoming hash
      if(fHash is None):
        fHash = hashlib.md5(open(f, 'rb').read()).hexdigest()

      # Get the already existing files hash
      destHash = hashlib.md5(open(duplicate, 'rb').read()).hexdigest()

      # If it's a match, bail and don't save this incoming file.
      if(fHash == destHash):
        #print 'Bailing, duplicate...'
        skipCopy = True
        break

      duplicate = thisDestDir + '/%s-%04d.' % (destFileName, suffix) + fExt
      suffix += 1

    # Different hash or not a duplicate, persist at the destination!
    if(skipCopy == False):
      if(move == False):
        shutil.copy2(f, duplicate)
      else:
        shutil.move(f, duplicate)
    else:
      if(move == True):
        os.remove(f)

  except Exception as e:

    if not os.path.exists(errorDir):
      os.makedirs(errorDir)

    if(move == False):
      shutil.copy2(f, errorDir + filename)
    else:
      shutil.move(f, errorDir + filename)

    print(e)
    print(traceback.extract_stack())
    problems.append(f)
  except:
    sys.exit("Execution stopped.")
   

###################### Main program ########################

def main(argv):

  # Validate required packages...
  checkForExiv2()

  parser = argparse.ArgumentParser()
  optional = parser._action_groups.pop() # Edited this line
  required = parser.add_argument_group('required arguments')
  
  required.add_argument('source', type=str, help='The source directory to read image/video files from.')
  required.add_argument('destination', type=str, help='The destination directory to put image/video files, renamed and with the proper folder structure')
  required.add_argument('type', type=str, help='The type of files to move. Specify one: photo, video')
  optional.add_argument('-m', '--move', action='store_true', help='Specify to move source files to their new location instead of copying.')
  parser._action_groups.append(optional) # added this line
  args = parser.parse_args()

  # Where the photos are and where they're going.
  sourceDir = args.source
  destDir = args.destination
  scanType = args.type.upper()
  if(scanType != 'PHOTO' and scanType != 'VIDEO'):
    print "Incorrect type specified! Must be either 'photo' or 'video'"
    sys.exit(1)
  
  errorDir = destDir + '/Unsorted/'
  move = args.move

  # Validate these directories exist...
  if not os.path.exists(sourceDir):
    print 'Source Directory does not exist!'
    sys.exit(1)
  if not os.path.exists(destDir):
    # os.makedirs(destDir)
    print 'Destination Directory does not exist!'
    sys.exit(1)

  # The format for the new file names.
  filenameFmt = "%Y%m%d-%H%M%S"

  # File Extensions we care about
  photoExtensions = ['.JPG', '.PNG', '.THM', '.CR2', '.NEF', '.DNG', '.RAW', '.NEF', '.JPEG']
  videoExtensions = ['.3PG', '.MOV', '.MPG', '.MPEG', '.AVI', '.3GPP', '.MP4']
  
  scanExtensions = photoExtensions
  if(scanType == 'VIDEO'):
    scanExtensions = videoExtensions

  # The problem files.
  problems = []

  # Get all the photos in the source directory
  #TODO: Handle videos, probably via parameter
  for extension in scanExtensions:
    for root, dirnames, filenames in os.walk(sourceDir):
      for filename in filenames:
        if filename.upper().endswith(extension):
          f = os.path.join(root, filename)
          print "Processing: %s..." % f
          handleFileMove(f, filename, filenameFmt, problems, move, sourceDir, destDir, errorDir)

  if(move == True):
    removeEmptyFolders(sourceDir, False)

  # Report the problem files, if any.
  if len(problems) > 0:
    print "\nProblem files:"
    print "\n".join(problems)
    print "These can be found in: %s" % errorDir
  else :
    print "\nSuccess!"

######################## Startup ###########################


if __name__ == "__main__":
   main(sys.argv[1:])
  
