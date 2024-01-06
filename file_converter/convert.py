import subprocess
import sys
from openai import OpenAI


class CommandParser:
    def __init__(self, query):
        self.query = query

    def parse(self):
        # Utilize OpenAI's API to interpret the command
        # and return the appropriate system command using streaming.

        client = OpenAI()

        system_prompt = f"""
        You are a command line utility that quickly and succinctly converts images and videos and manipulates them. When a user asks a question, you respond with the most relevant command that can be executed within the command line, along with the required packages that need to be installed. If the command has pre-requisite tools to install, install them first before proceeding. Your responses should be clear and console-friendly, remember the command you output must be directly copyable and would execute in the command line.

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

"""

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": "Answer this as briefly as possible: " + self.query,
            },
        ]
        completion_stream = client.chat.completions.create(
            messages=messages,
            model="gpt-4-1106-preview",
            stream=True,
        )

        response = ""

        for chunk in completion_stream:
            response += chunk.choices[0].delta.content or ""
            print(chunk.choices[0].delta.content or "", end="")

        return response


class CommandExecutor:
    @staticmethod
    def execute(command):
        try:
            subprocess.run(command, check=True, shell=True)
            print(f"Executed: {command}")
        except subprocess.CalledProcessError as e:
            print(f"An error occurred: {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python script.py 'conv <query>'")
        sys.exit(1)

    input_command = sys.argv[1]

    # query = input_command.split("conv ", 1)[1]
    print("Query:", input_command)
    parser = CommandParser(input_command)
    system_command = parser.parse()

    if system_command:
        CommandExecutor.execute(system_command)
    else:
        print("Could not parse or execute the command.")


if __name__ == "__main__":
    main()
