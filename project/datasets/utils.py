from pathlib import Path
from typing import Tuple, List

extensions = ['.jpg', '.png', '.bmp']


def get_files_by_category(data_path: str) -> Tuple[str, List[str]]:
    data_path = Path(data_path)
    for item in data_path.iterdir():
        if item.is_dir():
            label = item.name
            files = []
            for file in item.iterdir():
                if file.is_file() and file.suffix in extensions:
                    files.append(str(file))
            yield label, files
