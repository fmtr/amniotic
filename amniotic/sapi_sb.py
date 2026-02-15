import dotenv
import os
from aiohasupervisor import SupervisorClient

from corio import env

dotenv

ed = env.get_dict()

SUPERVISOR_API_URL = os.environ.get("http://supervisor/core/api/")
SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN")

client = SupervisorClient(SUPERVISOR_API_URL, SUPERVISOR_TOKEN)
