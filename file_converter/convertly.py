import argparse
import subprocess
import tempfile
import os
import configparser
import platform
import requests


class ConfigManager:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config_path = os.path.expanduser("~/.config/convertly/config.ini")
        if not os.path.exists(os.path.dirname(self.config_path)):
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(
                self.config_path, "w"
            ):  # Create the config file if it does not exist
                pass
        self.config.read(self.config_path)

    def get_api_key(self, key_name, section_name):
        api_key = os.getenv(key_name)

        if (
            not self.config.has_section(section_name)
            or "API_KEY" not in self.config[section_name]
        ):
            if not api_key:
                api_key = input(f"Please enter your {section_name} key: ")
            if not self.config.has_section(section_name):
                self.config.add_section(section_name)
            self.config.set(section_name, "API_KEY", api_key)
            with open(self.config_path, "w") as configfile:
                self.config.write(configfile)
        else:
            api_key = self.config[section_name]["API_KEY"]
        return api_key

    def set_api_key(self, key_name, section_name, new_api_key):
        if not self.config.has_section(section_name):
            self.config.add_section(section_name)
        self.config.set(section_name, "API_KEY", new_api_key)
        with open(self.config_path, "w") as configfile:
            self.config.write(configfile)


class CommandParser:
    def __init__(self, query, history_manager, config_manager, new_api_key=None):
        self.query = query
        self.history_manager = history_manager
        self.config_manager = config_manager
        if new_api_key:
            self.config_manager.set_api_key("OPENAI_API_KEY", "OPENAI", new_api_key)

    def get_command(self, api_key, messages):
        # url = "http://127.0.0.1:5000/api"
        url = "https://conv.pavitarsaini.com/api"

        data = {
            "api_key": api_key,
            "messages": messages,
        }
        request = requests.post(url, json=data)
        try:
            data = request.json()
        except Exception as e:
            print(f"Error: {e}")
            data = {"status": 500, "response": "Error: " + str(e)}
        response = data.get("response", "")
        status_code = int(data.get("status", 500))

        if status_code != 200:
            raise Exception(f"Error: {status_code} - {response}")

        return response, status_code

    def parse(self):
        api_key = self.config_manager.get_api_key("OPENAI_API_KEY", "OPENAI")
        history = self.history_manager.get_recent_history(5)
        history_prompt = self._generate_history_prompt(history)
        system_prompt = self._generate_system_prompt()

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": "Answer this using the latest context, remember to explain your thinking using the echo command(echo 'explanation') and output code after. Task: "
                + self.query,
            },
        ]

        if history:
            messages.insert(
                1,
                {
                    "role": "user",
                    "content": history_prompt
                    + ' NOTE: If the last command produced an error you must explain the problem and the solution to that problem".',
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
            "For context, here's the history of the last five questions, answers and the status of their execution, if an error occured you must not use that command again. \n\n"
            + "\n".join(history)
        )

    def _generate_internal_error_prompt(self):
        latest_history_status = self.history_manager.get_recent_history(1)
        status_part = "No error"
        if latest_history_status:
            status_part = latest_history_status[0].split("Status: ")[-1]

        return f"""If the following does not contain "No error", then "{status_part}", YOU MUST echo why the error occurred FIRST in the format echo "Error: (error)", and consider it when generating the next command, only if it's relevant. If there is no error, IGNORE this."""

    def _generate_system_prompt(self):

        return f"""You are a command line utility for the {platform.system()} OS that quickly and succinctly converts images, videos, files and manipulates them. When a user asks a question, you MUST respond with ONLY the most relevant command that will be executed within the command line, along with the required packages that need to be installed. If absolutely necessary, you may execute Python code to do a conversion by creating a python file and running it. Your responses should be clear and console-friendly. If there are file or folder paths, then they MUST be quoted in your response.

        Things to NOT do:

        - Do not include codeblocks or any ``` in your response, this is not a bash script, it is a command line utility. Commands should be directly executable in the command line.
        - Do not assume a user has pre-requisite packages installed, always install it anyways. 
        - Do not rename file extensions for conversions, unless the user specifically asks for it.

Here's how your responses should look:

EXAMPLE 1

<Users Question>
conv file.webp to png
<Your Answer>
echo "Explanation: I will use dwebp to convert the file to a png."
dwebp "file.webp" -o "file.png"
<User Question>
echo "Explanation: To rotate the image by 90 degrees, I will use imagemagick."
rotate that image by 90 degrees
<Your Answer>
brew install imagemagick
convert "file.png" -rotate 90 "rotated_file.png"

EXAMPLE 2

<Users Question>
convert a video in /path/to/video.mp4 to a gif
<Your Answer>
echo "Explanation: I will use ffmpeg to convert the video to a gif."
ffmpeg -i "/path/to/video.mp4" "/path/to/video.gif"

EXAMPLE 3

<Users Question>
convert my pdf to docx, the file is /Users/path/file.pdf
<Your Answer>
echo "Explanation: I will use pdf2docx to convert the pdf to a docx."
pip install pdf2docx
python3 -c "from pdf2docx import parse; pdf_file = r'/Users/path/file.pdf'; docx_file = r'/Users/path/file.docx'; parse(pdf_file, docx_file, start=0, end=None)"

EXAMPLE 4

<Users Question>
copy all of Documents/Screenshots to a folder called Screenshots2 in the same directory
<Your Answer>
echo "Explanation: I will use cp to copy the folder to a folder called Screenshots2."
cp -a "Documents/Screenshots Documents/test"


"""


class CommandExecutor:
    @staticmethod
    def execute(command):
        status = ""
        if command.startswith('echo "Error:'):
            print(
                f"\033[1;31;40mThe previous command failed: {command.split('Error: ')[-1]}\033[0m"
            )
            status = f"An error occurred while executing the command: {command.split('Error: ')[-1]}"
        else:
            try:
                subprocess.run(command, check=True, shell=True, text=True)
                print(f"\033[1;32;40mExecuted: {command}\033[0m")
                # print(f"Output: {result.stdout}")
                status = "Success"
            except subprocess.CalledProcessError as e:
                print(
                    f"\033[1;31;40mAn error occurred while executing the command: {e}\033[0m"
                )
                # figure out a better way to capture relevant output and feed it back
                print(f"Error info: {e.stderr}")
                status = f"An error occurred while executing the command: {e}, Error info: {e.stderr}"
        return status


class HistoryManager:
    def __init__(self, history_file_path):
        self.history_file_path = history_file_path

    def clear_history(self):
        with open(self.history_file_path, "w") as f:
            f.write("")

    def get_recent_history(self, n):
        if not os.path.exists(self.history_file_path):
            open(self.history_file_path, "w").close()

        with open(self.history_file_path, "r") as f:
            blocks = f.read().split("\n\n")[:-1]

        return blocks[-n:]

    def modify_history(self, query, response, status):
        with open(self.history_file_path, "a") as f:
            f.write(f"Question: {query}\nAnswer: {response}\nStatus: {status}\n\n")


def main():
    temp_dir = tempfile.gettempdir()
    history_file_path = os.path.join(temp_dir, "history.txt")
    history_manager = HistoryManager(history_file_path)
    config_manager = ConfigManager()

    parser = argparse.ArgumentParser(
        description="Conv is a command line tool to easily execute file conversions, image manipulations, and file operations quickly."
    )
    parser.add_argument("query", type=str, nargs="*", help="The query to be processed.")
    parser.add_argument("--clear", action="store_true", help="Clear the history.")
    parser.add_argument(
        "--hist", action="store_true", help="View the recent history of queries."
    )
    parser.add_argument("--key", type=str, help="Enter a new OpenAI API key.")

    args = parser.parse_args()

    if args.clear:
        history_manager.clear_history()
        print("\033[1;32;40mHistory cleared.\033[0m")
        return

    if args.hist:
        history = history_manager.get_recent_history(5)
        print("\033[1;32;40mRecent History:\033[0m")
        for item in history:
            print(item + "\n")
        return

    if args.key:
        new_api_key = args.key
        command_parser = CommandParser("", history_manager, config_manager, new_api_key)
        print(f"\033[1;32;40mAPI Key updated successfully to: {new_api_key}\033[0m")
        return

    if not args.query:
        print(
            "\033[1;31;40mUsage: python script.py 'conv <query>' or '--clear' to clear history or '--hist' to view history\033[0m"
        )
        return

    query = " ".join(args.query)
    print("\033[1;34;40mQuerying: " + query + "\033[0m")

    command_parser = CommandParser("", history_manager, config_manager, args.key)
    system_command = command_parser.parse()

    if system_command:
        print("\033[1;36;40mRunning command: " + system_command + "\033[0m")
        status = CommandExecutor.execute(system_command)
        history_manager.modify_history(query, system_command, status)
    else:
        print(
            "Could not parse or execute the command. Please ensure the command is valid."
        )


if __name__ == "__main__":
    main()
