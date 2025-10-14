import logging
import sys

logging.basicConfig(
    level=logging.DEBUG,  # Set the lowest level to capture everything
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout  # Log to the console
)

# You can get the logger instance to use in other files if needed
log = logging.getLogger(__name__)