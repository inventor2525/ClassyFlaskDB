from ClassyFlaskDB.Flaskify.Loggers.LoggerModel import *
import os
from datetime import datetime
from werkzeug.datastructures import FileStorage
from flask import request
import mimetypes

class Logger:
    def __init__(self, log_json=True, log_files=True, name="DefaultLogger", files_folder="server_log_files"):
        self.log_json = log_json
        self.log_files = log_files

        self.name = name
        self.files_folder = files_folder

    def __call__(self, request: request, *args, **kwargs):
        with logger_engine.session() as session:
            now = datetime.now()
            now_str = now.strftime("%Y-%m-%d_%H-%M-%S.%f")

            entry = Entry(
                logger_name=self.name,
                ip_address=request.remote_addr,
                endpoint=request.path,
                method=request.method,
                timestamp=now
            )
            if self.log_json and request.content_type == 'application/json': #json
                entry.json_data = request.json
            
            if self.log_files and request.content_type.startswith('multipart/form-data'): #files
                os.makedirs(self.files_folder, exist_ok=True)
                for filename, file in request.files.items():
                    dir_path = os.path.join(self.files_folder, self.name, *request.path.strip('/').split('/'), request.method)
                    os.makedirs(dir_path, exist_ok=True)

                    file_type = file.content_type  # MIME type
                    
                    # Derive the extension from the MIME type
                    extension = '' if file_type is None else (mimetypes.guess_extension(file_type) or '')

                    # Construct the final file path with the appropriate extension
                    file_path = os.path.join(dir_path, f"{filename}_{now_str}{extension}")
                    file.seek(0)
                    file.save(file_path)

                    # Append the file reference to the entry
                    entry.files.append(FileReference(
                        name=file.filename,
                        content_length=file.content_length,
                        file_path=file_path,
                        file_type=file_type
                    ))

            session.add(entry)
            session.commit()
