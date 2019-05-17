from sqs.pluglib import plg_mgr
import subprocess
import argh



@plg_mgr.register
@argh.arg('-f', '--full-output', help="Displays the full output from 'git status -uno'")
def update(full_output=False):
    """
    Checks to see if an update is available. If so, ask the user if they want
    to get the update now.

    This command runs the following git commands:
    $ git remote update
    $ git status -uno

    The latter command will tell if there is an update available.  If there is
    then the following command is executed if the user responds y or yes to the prompt.
    $ git pull origin master

    """
    cmd = 'git remote update'
    output = subprocess.check_output(cmd).decode()

    cmd = 'git status -uno'
    output = subprocess.check_output(cmd).decode()
    if full_output:
        print(f"Output from {cmd}\n" + '-'*30 + '\n')
        print(output + "\n")

    if "Your branch is up-to-date with 'origin/master'." in output:
        print('SQS is up to date')
    elif "Your branch is behind 'origin/master' by" in output:
        answer = input('An update for SQS is available.  Would you like to update? (y/n)')
        if answer.lower() in ('y', 'yes'):
            cmd = 'git pull origin master'
            output = subprocess.check_output(cmd).decode()
            print(output)


