import requests
import click
import os

@click.command("qsub")
@click.argument("command", nargs=1)
@click.argument("args", nargs=-1)
@click.option("--priority", default=10, type=int)
@click.option("--logfile", default='', type=str)
def qsub(command, args, priority=10, logfile=None):
    
    command = command + " " + " ".join(f'"{arg}"' for arg in  args)
    print(command)
    working_dir = os.getcwd()

    message = {
        "command": command,
        "working_dir": working_dir,
        "logfile": logfile,
        "priority": priority
    }

    response = requests.post("http://127.0.0.1:8000/qsub", json=message)
    print(response.text)