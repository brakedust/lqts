import subprocess
import time

import psutil

command = r'C:\Users\CampbellBL\work\apps\tempest\tempest31bin\bin\Tempest.Console.exe "--database" "G:/Active/projects/lsc/TempestSims/FY23-sonarslam/execute/DDGX_Hull_2307.7-DWL-FMC36/2023-08-11T144232/production/setup/production_000/_DDGX_Hull_2307.7-DWL-FMC36_db.xml" "--run" "--groupcount" "800" "--groupid" "1" "--resultsDir" "G:\Active\projects\lsc\TempestSims\FY23-sonarslam\execute\DDGX_Hull_2307.7-DWL-FMC36\2023-08-11T144232\production\setup\production_000\..\..\raw\export"'

p = subprocess.Popen(
    command,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    shell=False,
)

for i in range(20):
    # time.sleep(1)
    line = p.stdout.read(128)
    line = line.decode("utf-8")
    print(line)

p.terminate()
