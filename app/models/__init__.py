""" This file contains schema definitions for the application. """

from sqlalchemy.ext.declarative import declarative_base

from .sessions import Session
from .message import Message
from .artifact import Artifact
from .job_posting import JobPosting
from .hiring import HiringContext
from .checklist import ChecklistItem

Base = declarative_base()