import argparse
import subprocess
from openpipe import OpenAI
import tempfile
import os
import configparser
import platform
import requests


class ConfigManager:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read("config.ini")

    def get_api_key(self, key_name, section_name):
        api_key = os.getenv(key_name)
        if (
            not self.config.has_section(section_name)
            or "API_KEY" not in self.config[section_name]
        ):
            if not api_key:
                api_key = input(f"Please enter your {section_name} key: ")
            self.config[section_name] = {"API_KEY": api_key}
            with open("config.ini", "w") as configfile:
                self.config.write(configfile)
        return api_key


class CommandParser:
    def __init__(self, query, history_file_path):
        self.query = query
        self.history_file_path = history_file_path
        self.config_manager = ConfigManager()

    def get_command(self, api_key, messages):
        url = "https://convertly-41cf77f682ee.herokuapp.com/api"
        data = {
            "api_key": api_key,
            "messages": messages,
        }
        data = requests.post(url, json=data).json()
        response = data.get("response", "")
        status_code = int(data.get("status", 500))

        if status_code != 200:
            raise Exception(f"Error: {status_code} - {response}")

        return response, status_code

    def parse(self):
        api_key = self.config_manager.get_api_key("OPENAI_API_KEY", "OPENAI")
        history = get_recent_history(5, self.history_file_path)
        history_prompt = self._generate_history_prompt(history)
        system_prompt = self._generate_system_prompt()

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": "Answer this as briefly as possible: " + self.query,
            },
        ]

        if history:
            messages.insert(
                1,
                {
                    "role": "user",
                    "content": "For context, here are recent question and answers, so if the current question is ambigous see if theres context here. Use this to also keep file locations in mind, in case files are moved around or names changed, use the latest context from here.\n\n"
                    + history_prompt,
                },
            )
        print(f"\033[1;33;40mRunning...\033[0m", end="\r")
        response, status_code = self.get_command(api_key, messages)
        if status_code != 200:
            error_message = response.get("error", "Unknown error")
            print(
                f"\033[1;31;40mError: Unable to get command, status code: {status_code}, error: {error_message}\033[0m"
            )

        return response

    def _generate_history_prompt(self, history):
        return (
            "For context, here are recent question and answers, use this in case queries are confusing or if a past query has failed. In case there are amiguity with the queries, use this as additional context. \n\n"
            + "\n".join(history)
        )

    def _generate_system_prompt(self):
        return f"""
        You are a command line utility for the {platform.system()} OS that quickly and succinctly converts images, videos, files and manipulates them. When a user asks a question, you MUST respond with ONLY the most relevant command that will be executed within the command line, along with the required packages that need to be installed. If absolultely necessary, you may execute Python code to do a conversion. Your responses should be clear and console-friendly, remember the command you output must be directly copyable and would execute in the command line. We only want you to execute the command to result in an output.

        Things to NOT do:

        - Do not include ```sh``` or ```bash``` in your response, this is not a bash script, it is a command line utility. Run commands directly.
        - Do not assume a user has pre-requisite packages installed, always install it anyways. 

Here's how your responses should look:

EXAMPLE 1

<Users Question>
conv file.webp to png
<Your Answer>
dwebp file.webp -o file.png
<User Question>
rotate that image by 90 degrees
<Your Answer>
brew install imagemagick
convert file.png -rotate 90 rotated_file.png

EXAMPLE 2

<Users Question>
rotate an image by 90 degrees
<Your Answer>
brew install imagemagick
convert file.png -rotate 90 rotated_file.png

EXAMPLE 3

<Users Question>
convert a video in /path/to/video.mp4 to a gif
<Your Answer>
ffmpeg -i /path/to/video.mp4 /path/to/video.gif

EXAMPLE 4

<Users Question>
avif to png for file.avif
<Your Answer>
magick file.avif file.png

EXAMPLE 5

<Users Question>
convert my pdf to docx, the file is /Users/path/file.pdf
<Your Answer>
pip install pdf2docx
python3 -c "from pdf2docx import parse; pdf_file = r'/Users/path/file.pdf'; docx_file = r'/Users/path/file.docx'; parse(pdf_file, docx_file, start=0, end=None)"

EXAMPLE 6

<Users Question>
copy all of Documents/Screenshots to a folder called Screenshots2 in the same directory
<Your Answer>
cp -a Documents/Screenshots Documents/test


"""


class CommandExecutor:
    @staticmethod
    def execute(command):
        status = ""
        try:
            subprocess.run(command, check=True, shell=True)
            print(f"\033[1;32;40mExecuted: {command}\033[0m")
            status = "Success"
        except subprocess.CalledProcessError as e:
            print(
                f"\033[1;31;40mAn error occurred while executing the command: {e}\033[0m"
            )
            status = f"An error occurred while executing the command: {e}"
        return status


def clear_history(history_file_path):
    with open(history_file_path, "w") as f:
        f.write("")


def get_recent_history(n, history_file_path):
    if not os.path.exists(history_file_path):
        open(history_file_path, "w").close()

    with open(history_file_path, "r") as f:
        blocks = f.read().split("\n\n")[:-1]

    return blocks[-n:]


def modify_history(history_file_path, query, response, status):
    with open(history_file_path, "a") as f:
        f.write(f"Question: {query}\nAnswer: {response}\nStatus: {status}\n\n")


def main():
    temp_dir = tempfile.gettempdir()
    history_file_path = os.path.join(temp_dir, "history.txt")

    parser = argparse.ArgumentParser(
        description="Conv is a command line tool to easily execute file conversions, image manipulations, and file operations quickly."
    )
    parser.add_argument("query", type=str, nargs="*", help="The query to be processed.")
    parser.add_argument("--clear", action="store_true", help="Clear the history.")
    parser.add_argument(
        "--hist", action="store_true", help="View the recent history of queries."
    )

    args = parser.parse_args()

    if args.clear:
        clear_history(history_file_path)
        print("\033[1;32;40mHistory cleared.\033[0m")
        return

    if args.hist:
        history = get_recent_history(5, history_file_path)
        print("\033[1;32;40mRecent History:\033[0m")
        for item in history:
            print(item + "\n")
        return

    if not args.query:
        print(
            "\033[1;31;40mUsage: python script.py 'conv <query>' or '--clear' to clear history or '--hist' to view history\033[0m"
        )
        return

    query = " ".join(args.query)
    print("\033[1;34;40mQuerying: " + query + "\033[0m")

    command_parser = CommandParser(query, history_file_path)
    system_command = command_parser.parse()

    if system_command:
        print("\033[1;36;40mRunning command: " + system_command + "\033[0m")
        status = CommandExecutor.execute(system_command)
        modify_history(history_file_path, query, system_command, status)
    else:
        print(
            "Could not parse or execute the command. Please ensure the command is valid."
        )


if __name__ == "__main__":
    main()
