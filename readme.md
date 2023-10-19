# smToDodo
Converts .ssc/.sm files from Stepmania to Dodo Re Mi from Jackbox Party Pack 10.

## Download
Check out the releases tab to the right! You can either download an .exe version (for Windows), or you can download the Python script.

## Setup
Besides smToDodo, you need ffmpeg downloaded and added to the PATH enviroment variable of your system. <br>
Additionally, before using smToDodo for the first time, you need to set the song path in the config (see smToDodo.ini). <br>
For the Python script, you need to setup an enviroment with simfile and pydub as extra packages. The exact versions I've used can be found on top of the python script, if needed.

## Usage
Generally, you use it by typing `smToDodo [simfile_path]` into your command prompt, where `[simfile_path]` is either the folder of the simfile, or the .ssc/.sm file itself. <br>
It's also recommended to take a look at the help via `smToDodo -h`, as it contains extra options (most importantly hitsounds).