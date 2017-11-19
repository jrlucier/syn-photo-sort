## Intro
This script will bucket photos from a given source directory into a dated tree structure in a destination directory.

This script was written to run on a Synology NAS with DiskStation on board (python 2.7, and exiv2 installed).  
The idea being I wanted all backed up photos (using either DS Photo or DS File) to get automatically moved, sorted, 
and structured by date using their EXIF date and time.  If no EXIF date and time are found, it falls back to using 
the file systems "last modified" date and time.

The destination structure looks like he following:
```
Dest/
  2015/
    02/
      02FEB2015/
        20150202-183511.jpg
        20150202-193501.jpg
```


## Usage
These are the program arguments:
```
usage: syn_photo_sort.py [-h] [-m] source destination type

required arguments:
  source       The source directory to read image/video files from.
  destination  The destination directory to put image/video files, renamed and
               with the proper folder structure
  type         The type of files to move. Specify one: photo, video

optional arguments:
  -h, --help   show this help message and exit
  -m, --move   Specify to move source files to their new location instead of
```

The source directory is scanned recursively, for whatever kind of file you specified via the type flag of "photo" or 
"video".  The types and extensions are as follows:

 * photo: `'.JPG', '.PNG', '.THM', '.CR2', '.NEF', '.DNG', '.RAW', '.NEF', '.JPEG'`
 * video: `'.3PG', '.MOV', '.MPG', '.MPEG', '.AVI', '.3GPP', '.MP4'`

If you specify the `-m` or `--move` flag, it will move the source file to its intended destination and delete it from 
the source directory.  It will also clean up any existing empty folders that might exist.  It will however leave the 
root source directory.


## Setup For Synology NAS
SCP the file up, and place it at `/usr/local/bin/syn_photo_sort` (no need for the `.py` extension).  You should now be able to call it at any time using 
`syn_photo_sort`.  Once there, setup your cron job by using DSM and visiting the "Task Scheduler".  Create a new user
`user defined script` and place all the command line calls you want to run.  Such as:
```bash
syn_photo_sort -m /data/source /data/destination photo
```
