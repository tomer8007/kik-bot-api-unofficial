import os

from dotenv import dotenv_values

__all__ = ['env']

# Get the path of the current file, so we can import our .env
# configuration from other scripts, regardless of
# working directory during execution.
__dir_path = os.path.dirname(os.path.realpath(__file__))

# Load the .env file
env = {
    **os.environ,
    **dotenv_values(f'{__dir_path}/../../.env')
}
