from pydantic import BaseModel , Field

class File(BaseModel):
    path: str = Field(description="The path to the file to be created or modified")
    purpose: str = Field(description="The purpose of the file, e.g. 'main application logic', 'data processing module', etc.")
    
    
class Plan(BaseModel):
    name: str = Field(description="The name of app to be built")
    description: str = Field(description="A online description of the app to be built, e.g. 'A web application for managing personal finances")
    techstack: str = Field(description="The tech stack to be used for building the app, e.g. 'Python', 'javascript', 'react', 'flask', etc.")
    features: list[str] = Field(description="A list of features that the app should have, e.g. 'user authentication', 'data visualization', 'API integration', etc.")
    files: list[File] = Field(description="A list of files that need to be created , along with a 'path' and 'purpose'.")