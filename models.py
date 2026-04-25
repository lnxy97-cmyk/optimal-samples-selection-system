from dataclasses import dataclass


@dataclass
class Record:
    record_name: str
    record_content: str
    created_at: str