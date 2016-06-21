import subprocess

cmd = 'cmd.exe d:/test.bat'
p = subprocess.Popen('cmd.exe /c' + 'd:/test.bat abc', stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

