import unittest
import tempfile
import shutil
from pathlib import Path
import os
import sys

# Add parent to path to import utils
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.io import write_text_atomic, save_json_atomic, load_json, file_lock

class TestIOUtilities(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_write_text_atomic(self):
        test_file = self.test_dir / "test.txt"
        content = "Hello, strict engine!"
        
        # Test creation
        write_text_atomic(test_file, content)
        self.assertTrue(test_file.exists())
        self.assertEqual(test_file.read_text(encoding="utf-8"), content)
        
        # Test overwrite
        new_content = "Overwritten content!"
        write_text_atomic(test_file, new_content)
        self.assertEqual(test_file.read_text(encoding="utf-8"), new_content)
        
        # Ensure no dangling tmp files
        tmp_files = list(self.test_dir.glob("*.tmp"))
        self.assertEqual(len(tmp_files), 0)

    def test_json_atomic_read_write(self):
        json_file = self.test_dir / "data.json"
        data = {"key": "value", "list": [1, 2, 3]}
        
        # Test write
        save_json_atomic(json_file, data)
        self.assertTrue(json_file.exists())
        
        # Test read
        loaded = load_json(json_file)
        self.assertEqual(loaded, data)

    def test_file_lock(self):
        lock_path = self.test_dir / "test.lock"
        
        # Test locking creates the lock file
        with file_lock(lock_path):
            self.assertTrue(lock_path.exists())
            
            # Nested lock should fail (file is locked)
            with self.assertRaises(Exception):
                # Try to acquire another lock on the same file to trigger error
                with file_lock(lock_path, timeout=0.1):
                    pass
                
        # Test lock file is cleaned up after context exit
        self.assertFalse(lock_path.exists())

if __name__ == "__main__":
    unittest.main()
