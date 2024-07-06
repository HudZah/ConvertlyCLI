import argparse
import subprocess
import tempfile
import os
import configparser
import platform
import anthropic


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
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_KEY"))
        try:
            message = client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=1024,
                temperature=0.5,
                system='You will provide runnable commands for file conversion tasks in the command line. It follows these guidelines:\n\n- Uses built-in Unix commands whenever possible\n- Can run multiple commands and include multiple lines if needed\n- May install libraries for intricate conversion tasks\n- When creating directories for output files, use the same path as the input file unless specified otherwise\n- Ignores format codes in file output names\n- Uses "magick" instead of "convert" or "magick convert" for ImageMagick commands\n\n\nBad outputs are:\n- Explanations or commentary on the commands\n- Anything other than the runnable command itself\n- Commands that create directories in incorrect locations or use inconsistent paths\n\n\n<examples>\n<example_docstring>\nThis example demonstrates a more complex conversion.\n</example_docstring>\n\n<example>\n<user_query>Convert all .tiff files in the current directory to .jpg, resize them to 800x600, and apply a sepia filter.</user_query>\n\n<assistant_response>\nfor file in *.tiff; do\n    output_file="${file%.tiff}.jpg"\n    magick "$file" -resize 800x600 -sepia-tone 80% "$output_file"\ndone\n</assistant_response>\n</example>\n\n<example_docstring>\nThis example shows how to convert a video file to multiple formats while creating the output directory correctly.\n</example_docstring>\n\n<example>\n<user_query>Convert /Users/username/Videos/input.mp4 to gif, mp4 (compressed), and mp3. Save the outputs in a new folder called "converted" in the same directory as the input.</user_query>\n\n<assistant_response>\ninput_dir=$(dirname "/Users/username/Videos/input.mp4")\nmkdir -p "$input_dir/converted" && \\\nffmpeg -i "/Users/username/Videos/input.mp4" -vf "fps=10,scale=320:-1:flags=lanczos" "$input_dir/converted/input.gif" && \\\nffmpeg -i "/Users/username/Videos/input.mp4" -c:v libx264 -crf 23 -preset medium -c:a aac -b:a 128k "$input_dir/converted/input_compressed.mp4" && \\\nffmpeg -i "/Users/username/Videos/input.mp4" -vn -acodec libmp3lame -b:a 128k "$input_dir/converted/input.mp3"\n</assistant_response>\n</example>\n</examples>',
                messages=messages,
            )

            response_text = str(message.content[0].text) if message.content else ""
            input_tokens = message.usage.input_tokens
            output_tokens = message.usage.output_tokens

            print(f"Input tokens: {input_tokens}")
            print(f"Output tokens: {output_tokens}")

            return response_text, 200
        except Exception as e:
            return str(e), 400

    def parse(self):
        api_key = self.config_manager.get_api_key("OPENAI_API_KEY", "OPENAI")
        history = self.history_manager.get_recent_history(5)
        # history_prompt = self._generate_history_prompt(history)
        system_prompt = self._generate_system_prompt_claude()

        messages = [
            {
                "role": "user",
                "content": f"Answer this using the latest context. Task: {self.query}",
            }
        ]

        # if history:
        #     messages.insert(
        #         1,
        #         {
        #             "role": "user",
        #             "content": history_prompt
        #             + ' NOTE: If the last command produced an error you must explain the problem and the solution to that problem".',
        #         },
        #     )

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
            "Here's the history of the last five questions, answers and the status of their execution, if an error occured you must not use that command again. \n\n"
            + "\n".join(history)
        )

    def _generate_internal_error_prompt(self):
        latest_history_status = self.history_manager.get_recent_history(1)
        status_part = "No error"
        if latest_history_status:
            status_part = latest_history_status[0].split("Status: ")[-1]

        return f"""If the following does not contain "No error", then "{status_part}", YOU MUST echo why the error occurred FIRST in the format echo "Error: (error)", and consider it when generating the next command, only if it's relevant. If there is no error, IGNORE this."""

    def _generate_system_prompt_openai(self):

        return f"""
You will provide runnable commands for file conversion tasks in the command line. It follows these guidelines:

- Uses built-in Unix commands whenever possible
- Prioritize doing conversions in as few commands as possible
- May install libraries for intricate conversion tasks
- Exports the final version of a file to the same location as the origin, unless explicitly asked otherwise
- Ignores format codes in file output names
- Outputs only the executable command, as it will be executed directly in the command line
- Uses "magick" instead of "convert" or "magick convert" for ImageMagick commands

Good commands for this task are:
- Complete, runnable command-line scripts
- Multi-step conversion processes
- Scripts that may be reused or modified for similar conversion tasks

Bad outputs are:
- Explanations or commentary on the commands
- Anything other than the runnable command itself
- Including codefences, codeblocks or any ``` in your response. This is not markdown.

Usage notes:
- The assistant provides only the command(s) to be executed, with no additional text or explanation
- Commands should be complete and ready to run in a Unix-like environment
- If multiple steps are required, they should be combined into a single, executable script or command chain

These examples show simple file conversions.

Example 1:
Convert image.jpg to image.png

magick image.jpg image.png


Example 2:
Convert all .tiff files in the current directory to .jpg, resize them to 800x600, and apply a sepia filter.

for file in *.tiff; do
    output_file="${{file%.tiff}}.jpg"
    magick "$file" -resize 800x600 -sepia-tone 80% "$output_file"
done
"""

    def _generate_system_prompt_claude(self):
        return f"""
        You will provide runnable commands for file conversion tasks in the command line. It follows these guidelines:

- Uses built-in Unix commands whenever possible
- Can run multiple commands and include multiple lines if needed
- May install libraries for intricate conversion tasks
- Exports the final version of a file to the same location as the origin, unless explicitly asked otherwise
- Ignores format codes in file output names
- Outputs only the executable command, as it will be executed directly in the command line
- Uses "magick" instead of "convert" or "magick convert" for ImageMagick commands

Good commands for this task are:
- Complete, runnable command-line scripts
- Using the simplest, most common and most efficient commands
- Scripts that may be reused or modified for similar conversion tasks

Bad outputs are:
- Explanations or commentary on the commands
- Anything other than the runnable command itself

Usage notes:
- The assistant provides only the command(s) to be executed, with no additional text or explanation
- Commands should be complete and ready to run in a Unix-like environment
- If multiple steps are required, they should be combined into a single, executable script or command chain

<examples>
<example_docstring>
This example shows a simple file conversion command provided directly in the conversation.
</example_docstring>

<example>
<user_query>Convert image.jpg to image.png</user_query>

<assistant_response>
magick image.jpg image.png
</assistant_response>
</example>

<example_docstring>
This example demonstrates a more complex conversion.
</example_docstring>

<example>
<user_query>Convert all .tiff files in the current directory to .jpg, resize them to 800x600, and apply a sepia filter.</user_query>

<assistant_response>
for file in *.tiff; do
    output_file="${{file%.tiff}}.jpg"
    magick "$file" -resize 800x600 -sepia-tone 80% "$output_file"
done
</assistant_response>
</example>
</examples>
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

    command_parser = CommandParser(query, history_manager, config_manager, args.key)
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
