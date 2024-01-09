# Convertly

A command line tool to execute simple file conversions, image/video manipulations and folder changes. Use with ```conv <query>```. Convertly is constantly being fine-tuned using your outputs and will work better over time.

## Installation
```bash
pip install convertly
```
## Configuration
you will be prompted to configure the tool using your own OpenAI key. 

## Usage
To use Convertly, you can run the command followed by your query. For example:

```bash
> conv convert file.webp to file.png
* dwebp file.webp -o file.png
```
View the history of your queries with:
```bash
conv --history
```
Or reset your history with:
```bash
conv --clear
```
## Example Use Cases
```bash
> conv a video in /path/to/video.mp4 to a gif
* ffmpeg -i /path/to/video.mp4 /path/to/video.gif
```
```bash
> conv copy all of Documents/Screenshots to a folder called Screenshots2 in the same directory
* cp -a Documents/Screenshots Documents/test
```
```bash
> conv rotate image.png by 90 degrees
* brew install imagemagick
* convert image.png -rotate 90 rotated_file.png
```
## Support
Convertly wont be perfect; if you run into any issues, please send me a message or create an issue. 




