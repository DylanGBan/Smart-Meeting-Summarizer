# Smart Meeting Summarizer

> [!WARNING]
> This repo was just created but the project was started **August 30, 2025**.

## Description
Created a smart meeting summarizer that takes important summaries from meeting audio files. 
Takes in a mp3 file and then uses Whisper from OpenAI API, using moviepy to splice audio file into managable bites for Whisper to translate speech to text. 
Then using spaCy, keywords that are said in the meeting will be displayed in built points, with relevant context. Finially using OpenAI, the full transcript is summarized.
