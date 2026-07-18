from pathlib import Path
from dotenv import load_dotenv

# Load environment before any submodule reads os.environ
load_dotenv(Path(__file__).parent.parent / ".env")
