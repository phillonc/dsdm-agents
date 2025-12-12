#!/usr/bin/env python
"""
Convenience script to run the Flask Todo application.
"""
import os
import sys

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from app import create_app

if __name__ == '__main__':
    app = create_app()
    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000
    )
