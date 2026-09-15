from fastapi import UploadFile
from .BaseController import BaseController

class DataController(BaseController):
    def __init__(self):
        super().__init__()
        self.size_limit = self.app_settings.FILE_MAX_SIZE_MB * 1024 * 1024

    def validate_file(self, file: UploadFile):
        if file.content_type not in self.app_settings.FILE_ALLOWED_EXTENSIONS:
            return False, "file not allowed"
        if file.size is not None and file.size > self.size_limit:
            return False, "file size exceeds limit"
        return True
