import subprocess
import time
import os
import ollama
from ollama import AsyncClient
import asyncio
from pathlib import Path

from utils import utils


class OllamaCall:
    def __init__(self, model="llama3.2:latest" ):
        self.model = model
        self.current_chat = []
        self.name_current_chat = ""
        self.unsaved_text = []
        self.UI = None
        self.files = []
        self.processed_files = []



    async def send_message(self, prompt):
        # Append the user's message to the conversation history
        user_message = {'role': 'user', 'content': prompt}
        message = self.create_message(prompt)
        self.current_chat.append(user_message)
        self.unsaved_text.append(user_message)
        assistant_message = ""

        # Stream the response
        async for part in await AsyncClient().chat(model=self.model, messages=message, stream=True):
            # Check if part contains the expected keys; if not, break out of the loop
            if 'message' not in part or 'content' not in part['message']:
                break
            assistant_message+=part['message']['content']
            yield part['message']['content']


        self.current_chat.append({'role' : 'assistant', 'content' : assistant_message})
        self.unsaved_text.append({'role' : 'assistant', 'content' : assistant_message})
        self.save_chat_entry()


    def upload_file(self, file_path):
        if Path(file_path).suffix.lower() == '.pdf':
            self.files.append(file_path)
            pdf_content = utils.read_PDF(file_path)
            self.processed_files.append({"file": file_path,"type": '.pdf', "content": pdf_content})


    def create_message(self, prompt):
        context = ""
        file_content = ""
        if self.files:
            for file in self.processed_files:
                if file['type']=='.pdf':

                    file_content += (
                    "This PDF document has been uploaded and processed to extract its content. "
                    "The following text may contain formatting irregularities, especially in tables, formulas, or structured layouts. "
                    "Please focus on summarizing the main points, important findings, key concepts, and relevant details of the document. "
                    "Ignore less relevant parts like References, bibliographies, or sections focused solely on citations unless specifically asked. "
                    "If the document appears to be technical, highlight the core methodology, findings, and conclusions. "
                    "For non-technical documents, emphasize the primary topics, arguments, and takeaways. "
                    "Here is the content of the file:\n\n" + file['content']
                    )



        if self.current_chat:
            # Instruction to treat the following conversation as context only
            context += (
                "The following part between brackets is only for context. "
                "Do not react to it or include it in your response. "
                "It is here solely as memory to help with continuity.\n("
            )

            for old_conv in self.current_chat:
                context+=old_conv['role'] + ": " + old_conv['content'] + "\n"

            context += ") End of context.\n Now, answer the following question:\n"
        message = context + prompt + file_content
        return [{'role': 'user', 'content': message}]


    def generate_chat_name(self):
        content = ("The following is the first two messages of a conversation. Please think of an appropriate, short title"
                   "that describes this conversatioin. It should be as short as possible. Only output the title you came up with "
                   "and nothing else! It can not include any special symbols like question marks, dots or anything that can't be in"
                   "a file name of a windows machine. Here is the conversation: \n")
        for old_conv in self.current_chat:
            content += old_conv['role'] + ": " + old_conv['content'] + "\n"
        self.name_current_chat = ollama.chat(model='llama3.2:latest', messages=[{
            'role' : 'user',
            'content' : content
        }])['message']['content']

    def save_chat_entry(self):
        new_name = False
        if not self.name_current_chat:
            self.generate_chat_name()
            new_name = True

        # Define the file path
        utils.save_chat_entry(self.name_current_chat, self.unsaved_text)
        self.unsaved_text = []
        if self.files:
            utils.store_submitted_files(self.files, self.name_current_chat)
        if new_name:
            self.UI.load_chat_files()


    def reset_chat(self):
        # save unsaved conversation parts
        if self.unsaved_text:
            self.save_chat_entry()
        # Clears the conversation history
        self.current_chat = []
        self.files = []
        self.name_current_chat = ""
        self.UI.file_chips.controls.clear()
        self.UI.page.update()

    def new_chat(self):
        self.reset_chat()
        self.UI.chat_content = ""
        self.UI.update_prompt()

    def load_chat(self, file_name):
        # Reset chat data
        self.reset_chat()

        # File path for the chat file
        file_path = os.path.join("saved_chats", file_name)

        # Load chat lines and populate current_chat
        for message in utils.load_chat_file(file_path):
            self.current_chat.append(message)
        self.files = utils.load_submitted_files(os.path.join("saved_chats", file_name.replace(".txt", ".pkl")))
        self.UI.process_files(self.files)
        # Set the current chat name
        self.name_current_chat = file_name.replace(".txt", "")









