import argparse
import subprocess
from openai import OpenAI
import tempfile
import os
import configparser


class CommandParser:
    def __init__(self, query, history_file_path):
        self.query = query
        self.history_file_path = history_file_path

    def get_config(self):
        config = configparser.ConfigParser()
        config.read("config.ini")
        api_key = os.getenv("OPENAI_API_KEY")

        if not config.has_section("OPENAI") or "API_KEY" not in config["OPENAI"]:
            if not api_key:
                api_key = input("Please enter your OpenAI key: ")
            config["OPENAI"] = {"API_KEY": api_key}
            with open("config.ini", "w") as configfile:
                config.write(configfile)
        return config

    def parse(self):
        self.config = self.get_config()
        client = OpenAI(api_key=self.config["OPENAI"]["API_KEY"])

        # Retrieve the history file
        with open(self.history_file_path, "r") as f:
            history = f.read()

        history_prompt = (
            "For context, here are recent question and answers, so if the current question is ambigous see if theres context here. If a past query has failed and did not execute, take it into account and try something different when re-prompted.\n\n"
            + history
        )

        system_prompt = f"""
        You are a command line utility that quickly and succinctly converts images and videos and manipulates them. When a user asks a question, you respond with the most relevant command that can be executed within the command line, along with the required packages that need to be installed. If absolultely necessary, you may execute Python code to do a conversion. If the command has pre-requisite tools to install, install them first before proceeding. Your responses should be clear and console-friendly, remember the command you output must be directly copyable and would execute in the command line.

Here's how your responses should look:

EXAMPLE 1

<Users Question>
conv file.webp to png
<Your Answer>
`'dwebp file.webp -o file.png'`

EXAMPLE 2

<Users Question>
rotate an image by 90 degrees
<Your Answer>
`brew install imagemagick`
`convert file.png -rotate 90 rotated_file.png`

EXAMPLE 3

<Users Question>
convert a video in /path/to/video.mp4 to a gif
<Your Answer>
`ffmpeg -i /path/to/video.mp4 /path/to/video.gif`

EXAMPLE 4

<Users Question>
avif to png for file.avif
<Your Answer>
`magick file.avif file.png`

EXAMPLE 5

<Users Question>
convert my pdf to docx, the file is /Users/path/file.pdf
<Your Answer>
`pip install pdf2docx`
`python3 -c "from pdf2docx import parse; pdf_file = r'/Users/path/file.pdf'; docx_file = r'/Users/path/file.docx'; parse(pdf_file, docx_file, start=0, end=None)"`


"""
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

        completion_stream = client.chat.completions.create(
            messages=messages,
            model="gpt-4-1106-preview",
            stream=True,
            max_tokens=100,
        )

        response = ""

        for chunk in completion_stream:
            response += chunk.choices[0].delta.content or ""
            print(f"\033[1;33;40mRunning...\033[0m", end="\r")

        # Write the last 5 commands to the history file
        with open(self.history_file_path, "a") as f:
            f.write(f"Question: {self.query}\nAnswer: {response}\n\n")

        return response


class CommandExecutor:
    @staticmethod
    def execute(command):
        try:
            subprocess.run(command, check=True, shell=True)
            print(f"\033[1;32;40mExecuted: {command}\033[0m")
        except subprocess.CalledProcessError as e:
            print(
                f"\033[1;31;40mAn error occurred while executing the command: {e}\033[0m"
            )


def clear_history(history_file_path):
    with open(history_file_path, "w") as f:
        f.write("")


def main():
    temp_dir = tempfile.gettempdir()
    history_file_path = os.path.join(temp_dir, "history.txt")
    if not os.path.exists(history_file_path):
        with open(history_file_path, "w") as f:
            pass

    parser = argparse.ArgumentParser(
        description="Conv is a command line tool to easily execute file conversions, image manipulations, and file operations quickly."
    )
    parser.add_argument("query", type=str, nargs="*", help="The query to be processed.")
    parser.add_argument("--clear", action="store_true", help="Clear the history.")

    args = parser.parse_args()

    if args.clear:
        clear_history(history_file_path)
        print("\033[1;32;40mHistory cleared.\033[0m")
        return

    if not args.query:
        print(
            "\033[1;31;40mUsage: python script.py 'conv <query>' or '--clear' to clear history\033[0m"
        )
        return

    query = " ".join(args.query)
    print("\033[1;34;40mQuerying: " + query + "\033[0m")

    command_parser = CommandParser(query, history_file_path)
    system_command = command_parser.parse()

    if system_command:
        print("\033[1;36;40mRunning command: " + system_command + "\033[0m")
        CommandExecutor.execute(system_command)
    else:
        print(
            "Could not parse or execute the command. Please ensure the command is valid."
        )


if __name__ == "__main__":
    main()
