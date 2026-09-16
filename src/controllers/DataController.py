from fastapi import UploadFile
from .BaseController import BaseController
from .ProjectController import ProjectController
from models import ResponseSignal
import re
import os
class DataController(BaseController):
    def __init__(self):
        super().__init__()
        self.size_limit = self.app_settings.FILE_MAX_SIZE_MB * 1024 * 1024

    def validate_file(self, file: UploadFile):
        if file.content_type not in self.app_settings.FILE_ALLOWED_EXTENSIONS:
            return False, ResponseSignal.FILE_TYPE_NOT_SUPPORTED.value
        if file.size is not None and file.size > self.size_limit:
            return False, ResponseSignal.FILE_SIZE_EXCEEDS_LIMIT.value
        return True, ResponseSignal.FILE_VALIDATION_SUCCESS.value

    def clean_file_name(self, org_file_name: str):
        # Remove any characters that are not alphanumeric, underscores, hyphens, or dots
        cleaned_file_name = re.sub(r'[^\w.-]', '', org_file_name.strip())
        return cleaned_file_name

    def generate_unique_filename(self, org_file_name: str, project_id: str):
        random_key = self.generate_random_string()
        project_path = ProjectController().get_project_path(project_id=project_id)
        cleaned_file_name = self.clean_file_name(org_file_name)
        new_file_path = os.path.join(
            project_path,
            random_key + "_" + cleaned_file_name
        )
        while os.path.exists(new_file_path):
            random_key = self.generate_random_string()
            new_file_path = os.path.join(
            project_path,
            random_key + "_" + cleaned_file_name
        )
        return new_file_path

       
